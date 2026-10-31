r"""C47 BTC leads alts (FAMILIES_C.md "C47", registered 2026-10-18 before this file existed).

    .venv\Scripts\python.exe -m quant.run_c47 fetch    # download 1m klines (resumable, cached in data/c47)
    .venv\Scripts\python.exe -m quant.run_c47 dev      # generate trades + judge DEV only

BTC 1m: r5 >= 3 sigma5 and >= 0.5% (mirror down), 30-minute re-arm per direction. Laggards = live coins whose 5-minute
return is < 0.5x BTC's; the 5 lowest ratios enter at the next minute's open, 30-minute hold, stop 3 sigma5 of the coin.
Twins: same number of random eligible coins at every trigger. Results -> runs/ledger_c.jsonl.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import trades as T
from .eval_c import PERIODS, ledger, mins
from .paths import DATA, RUNS
from .run_c42_c43 import NFI5, REPS, bars5, coins, evaluate, period_gate

CACHE = DATA / "c47"
OUT = RUNS / "c_trades" / "C47" / "1m"
MONTHS = [str(p) for p in pd.period_range("2024-08", "2025-08", freq="M")]   # Aug 2024 = 24h warm-up only
DEV_LO, DEV_HI = pd.Timestamp("2024-09-01"), pd.Timestamp("2025-09-01")      # naive UTC (1m data is naive UTC)
URL = "https://data.binance.vision/data/futures/um/monthly/klines/{s}/1m/{s}-1m-{m}.zip"
HOLD, REARM, K, MIN_MOVE, LAG, TOPN = 30, 30, 3.0, 0.005, 0.5, 5


def fetch(coin: str) -> pd.DataFrame:
    f = CACHE / f"{coin}.parquet"
    if f.exists():
        return pd.read_parquet(f)
    parts = []
    for m in MONTHS:
        try:
            raw = urllib.request.urlopen(URL.format(s=f"{coin}USDT", m=m), timeout=120).read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            k = pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=range(6))
        k = k[pd.to_numeric(k[0], errors="coerce").notna()].astype(float)
        k.columns = ["t", "open", "high", "low", "close", "volume"]
        k["date"] = pd.to_datetime(k["t"].astype("int64"), unit="ms")
        parts.append(k[["date", "open", "high", "low", "close"]].astype({c: "float64" for c in ("open", "high", "low", "close")}))
    d = pd.concat(parts, ignore_index=True).drop_duplicates("date").sort_values("date").reset_index(drop=True) if parts \
        else pd.DataFrame(columns=["date", "open", "high", "low", "close"])
    CACHE.mkdir(parents=True, exist_ok=True)
    d.to_parquet(f)
    return d


def on_grid(d: pd.DataFrame, grid: pd.DatetimeIndex) -> dict:
    x = d.set_index("date").reindex(grid)
    return {k: x[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close")}


def sigma5(close: np.ndarray) -> np.ndarray:
    """std of 1m log returns over the previous 1,440 minutes x sqrt(5), known at a minute's close (incl. that minute)."""
    lr = pd.Series(np.log(close)).diff()
    return (lr.rolling(1440, min_periods=1200).std() * np.sqrt(5)).to_numpy()


def triggers(b: dict) -> list[tuple[int, int]]:
    c = b["close"]
    r5 = c / np.r_[np.full(5, np.nan), c[:-5]] - 1
    s5 = sigma5(c)
    out, last = [], {1: -10**9, -1: -10**9}
    for i in np.where(np.isfinite(r5) & np.isfinite(s5) & ((np.abs(r5) >= K * s5) & (np.abs(r5) >= MIN_MOVE)))[0]:
        d = 1 if r5[i] > 0 else -1
        if i - last[d] < REARM:
            continue
        last[d] = i
        out.append((int(i), d))
    return out


def funding_events(coin: str) -> pd.Series:
    fp = NFI5 / f"{coin}_USDT_USDT-1h-funding_rate.feather"
    if not fp.exists():
        return pd.Series(dtype=float)
    f = pd.read_feather(fp)
    return pd.Series(f.iloc[:, 1].to_numpy(dtype=float), index=f["date"].dt.tz_localize(None))


def trade(a: dict, s5: np.ndarray, i: int, side: int, cost_mult: float = 1.0) -> dict | None:
    """Entry at minute i+1 open, time exit at the close of minute i+30, stop 3 sigma5 of the coin."""
    e, end = i + 1, i + HOLD
    o, h, l, c = a["open"], a["high"], a["low"], a["close"]
    if end >= len(c) or not np.all(np.isfinite(c[i - 5:end + 1])) or not np.isfinite(s5[i]):
        return None
    px = o[e]
    stop = px * (1 - side * K * s5[i])
    sx = T.STOP_EXTRA * cost_mult
    x, reason, xp = end, "time", c[end]
    for j in range(e, end + 1):
        if (l[j] <= stop) if side == 1 else (h[j] >= stop):
            gap = (o[j] < stop) if side == 1 else (o[j] > stop)
            xp, x, reason = (o[j] if gap else stop) * (1 - side * sx), j, "stop"
            break
    gross = side * (xp / px - 1)
    mae = (np.min(l[e:x + 1]) / px - 1) if side == 1 else -(np.max(h[e:x + 1]) / px - 1)
    return {"e": e, "x": x, "side": side, "gross": gross, "reason": reason, "mae": mae,
            "cost": 2 * (T.FEE + T.SLIP) * cost_mult + (sx if reason == "stop" else 0.0)}


def generate() -> dict:
    btc = fetch("BTC")
    grid = pd.date_range(btc["date"].min(), btc["date"].max(), freq="1min")
    b = on_grid(btc, grid)
    trig = [(i, d) for i, d in triggers(b) if DEV_LO <= grid[i] < DEV_HI]
    c_b = b["close"]
    r5b = c_b / np.r_[np.full(5, np.nan), c_b[:-5]] - 1
    alts = [c for c in coins() if c != "BTC"]
    # one coin at a time (RAM): every eligible coin's would-be trade at every trigger
    per_trig = {i: [] for i, _ in trig}
    for coin in alts:
        a = on_grid(fetch(coin), grid)
        s5 = sigma5(a["close"])
        df5 = bars5(coin)
        el = pd.Series(T.eligible(df5, 288), index=df5["date"].dt.tz_localize(None))
        el = el.reindex(grid.floor("5min")).fillna(False).to_numpy(dtype=bool)
        fu = funding_events(coin)
        for i, d in trig:
            if not el[i] or not np.isfinite(a["close"][i]) or not np.isfinite(a["close"][i - 5]):
                continue
            t1 = trade(a, s5, i, d)
            if t1 is None:
                continue
            t2 = trade(a, s5, i, d, 2.0)
            et, xt = grid[t1["e"]], grid[t1["x"]] + pd.Timedelta(minutes=1)
            f = d * (float(fu[(fu.index > et) & (fu.index <= xt)].sum()) if len(fu) else 0.0)   # longs pay +funding
            a5 = a["close"][i] / a["close"][i - 5] - 1
            per_trig[i].append((a5 / r5b[i], coin, t1, t2, f))
        del a, s5
    rows, busy = [], {c: -1 for c in alts}
    cand_all = []                                   # per trigger: every eligible coin's would-be trade (for twins)
    for i, d in trig:
        cands = per_trig[i]
        if not cands:
            continue
        lag = sorted([x for x in cands if x[0] < LAG], key=lambda x: x[0])[:TOPN]
        cand_all.append((i, d, len(lag), [(x[2], x[4]) for x in cands]))
        for ratio, coin, t1, t2, f in lag:
            if t1["e"] <= busy[coin]:
                continue
            rows.append({"family": "C47", "coin": coin, "side": d, "entry_t": grid[t1["e"]], "exit_t": grid[t1["x"]],
                         "ret": t1["gross"] - t1["cost"] - f, "ret_x2": t2["gross"] - t2["cost"] - f, "gross": t1["gross"],
                         "funding": f, "mae": t1["mae"], "reason": t1["reason"], "bars": t1["x"] - t1["e"] + 1,
                         "cost": t1["cost"], "ratio": ratio, "btc_r5": r5b[i]})
            busy[coin] = t1["x"]
    t = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    t.to_parquet(OUT / "trades.parquet")
    # twins: at every trigger the same number of coins drawn at random from all eligible coins (not only laggards)
    rng = np.random.default_rng(47)
    tw = np.zeros(REPS)
    for _, _, n, pool in cand_all:
        if n == 0:
            continue
        r = np.array([p["gross"] - p["cost"] - f for p, f in pool])
        for k in range(REPS):
            tw[k] += r[rng.choice(len(r), size=min(n, len(r)), replace=False)].sum()
    np.save(OUT / "twins.npy", tw)
    q = pd.Series([grid[i] for i, _ in trig]).dt.to_period("Q").astype(str)
    return {"triggers": len(trig), "up": sum(d == 1 for _, d in trig), "down": sum(d == -1 for _, d in trig),
            "triggers_per_quarter": q.value_counts().sort_index().to_dict(),
            "triggers_with_laggards": sum(1 for x in cand_all if x[2] > 0),
            "laggard_avg_gross_pct": round(float(t["gross"].mean() * 100), 3) if len(t) else None,
            "random_avg_gross_pct": round(float(np.mean([p["gross"] for x in cand_all for p, _ in x[3]]) * 100), 3)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["fetch", "dev"])
    ap.add_argument("--budget", type=float, default=540)
    a = ap.parse_args()
    if a.stage == "fetch":
        t0 = time.time()
        for coin in ["BTC"] + [c for c in coins() if c != "BTC"]:
            if (CACHE / f"{coin}.parquet").exists():
                continue
            d = fetch(coin)
            print(f"  {coin}: {len(d)} minutes, {time.time() - t0:.0f}s", flush=True)
            if time.time() - t0 > a.budget:
                print("budget reached")
                return 3
        print("fetch complete")
        return 0
    info = generate()
    per = PERIODS["intra"]["dev"]
    t = pd.read_parquet(OUT / "trades.parquet")
    for col in ("entry_t", "exit_t"):
        t[col] = pd.to_datetime(t[col]).dt.tz_localize("UTC")
    tw = np.load(OUT / "twins.npy")
    r = evaluate("C47", t, per, mins(), tw)
    m = r["book"]
    pg, pg_name = period_gate("C47", r, 0.75, 2, 3)
    g = {"≥200 trades": m.get("trades", 0) >= 200, "PF ≥ 1.15": m.get("pf", 0) >= 1.15,
         "PF ≥ 1.0 at 2x costs": r["book_x2"].get("pf", 0) >= 1.0, "DD ≤ 35%": m.get("max_dd_pct", 100) <= 35,
         pg_name: pg, "beats 95% of random twins": r.get("twin_pct", 0) >= 95,
         "top coin ≤ 20% of profit": (m.get("top_coin_share") or 1) <= 0.20}
    verdict = "PASS DEV" if all(g.values()) else "FAIL DEV"
    r["data"] = info
    r["by_side"] = {s: {"trades": int((t.side == v).sum()), "avg_ret_pct": round(float(t.loc[t.side == v, "ret"].mean() * 100), 3)}
                    for s, v in (("long", 1), ("short", -1))}
    ledger({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "batch": "C47", "family": "C47", "tf": "1m",
            "stage": "dev", "result": r, "gates": g, "verdict": verdict})
    keys = ("book", "book_x2", "periods_detail", "by_cell", "all_signals", "by_side", "twin_pct", "data")
    print(json.dumps({k: r.get(k) for k in keys} | {"gates": g}, indent=1, default=str))
    print("VERDICT: C47", verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
