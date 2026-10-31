r"""C46 Coinbase premium (FAMILIES_C.md "C46", registered 2026-10-18 before this file existed).

    .venv\Scripts\python.exe -m quant.run_c46 dev      # download premium data (cached), generate trades, judge DEV only
    .venv\Scripts\python.exe -m quant.run_c46 valid    # refused without a recorded DEV pass
    .venv\Scripts\python.exe -m quant.run_c46 wf       # refused without a recorded VALID pass

Premium p = Coinbase BTC-USD / (Binance spot BTCUSDT x Coinbase USDT-USD) - 1 per 1h bar; z of its 4h mean vs the
previous 720 bars; z crossing +2 -> long, -2 -> short (re-arm at +-1); the 10 most liquid eligible live coins enter.
Data cache: data/c46/*.parquet. Trades -> runs/c_trades/C46/1h/<coin>.parquet; results -> runs/ledger_c.jsonl.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import trades as T
from .bars import bars
from .eval_c import PERIODS, WALK_FORWARD, ledger, mins
from .paths import DATA, RUNS
from .run_c42_c43 import REPS, coins, evaluate, period_gate, utc

CACHE = DATA / "c46"
OUT = RUNS / "c_trades" / "C46" / "1h"
START, END = pd.Timestamp("2020-12-01", tz="UTC"), pd.Timestamp("2026-03-26", tz="UTC")
DEV = ("2021-01-01", "2024-07-01")
UA = {"User-Agent": "quantlab-research"}


def _get(url: str):
    for k in range(5):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read())
        except Exception:
            time.sleep(2 + 3 * k)
    raise RuntimeError(url)


def coinbase(product: str) -> pd.Series:
    f = CACHE / f"cb_{product}.parquet"
    if f.exists():
        return pd.read_parquet(f)["close"]
    rows, t = [], START
    while t < END:
        e = min(t + pd.Timedelta(hours=300), END)
        rows += _get(f"https://api.exchange.coinbase.com/products/{product}/candles?granularity=3600"
                     f"&start={t:%Y-%m-%dT%H:%M:%SZ}&end={e:%Y-%m-%dT%H:%M:%SZ}")
        t = e
        time.sleep(0.15)
    d = pd.DataFrame(rows, columns=["t", "low", "high", "open", "close", "volume"]).drop_duplicates("t")
    d.index = pd.to_datetime(d["t"], unit="s", utc=True)
    s = d.sort_index()[["close"]]
    CACHE.mkdir(parents=True, exist_ok=True)
    s.to_parquet(f)
    return s["close"]


def binance_spot() -> pd.Series:
    f = CACHE / "bn_spot_BTCUSDT.parquet"
    if f.exists():
        return pd.read_parquet(f)["close"]
    rows, t = [], int(START.timestamp() * 1000)
    end = int(END.timestamp() * 1000)
    while t < end:
        k = _get(f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&startTime={t}&limit=1000")
        if not k:
            break
        rows += k
        t = k[-1][0] + 3600_000
        time.sleep(0.1)
    d = pd.DataFrame([(r[0], float(r[4])) for r in rows], columns=["t", "close"]).drop_duplicates("t")
    d.index = pd.to_datetime(d["t"], unit="ms", utc=True)
    s = d.sort_index()[["close"]]
    CACHE.mkdir(parents=True, exist_ok=True)
    s.to_parquet(f)
    return s["close"]


def premium() -> pd.DataFrame:
    """Hourly frame indexed by bar OPEN time: p, p4, z, long_sig, short_sig (signals known at that bar's close)."""
    cb, bn, u = coinbase("BTC-USD"), binance_spot(), coinbase("USDT-USD")
    idx = pd.date_range(START, END, freq="1h", inclusive="left")
    cb, bn = cb.reindex(idx), bn.reindex(idx)
    first_u = u.index.min()
    u = u.reindex(idx)
    u[idx < first_u] = 1.0                                   # registered: USDT-USD not listed yet -> 1.0
    p = cb / (bn * u) - 1
    p4 = p.rolling(4, min_periods=4).mean()
    base = p4.shift(1).rolling(720, min_periods=600)
    z = (p4 - base.mean()) / base.std()
    zl = z.to_numpy()
    long_sig, short_sig = np.zeros(len(z), bool), np.zeros(len(z), bool)
    arm_l = arm_s = True
    for i in range(1, len(zl)):
        if not np.isfinite(zl[i]):
            continue
        if zl[i] < 1:
            arm_l = True
        if zl[i] > -1:
            arm_s = True
        prev = zl[i - 1]
        if arm_l and zl[i] >= 2 and (not np.isfinite(prev) or prev < 2):
            long_sig[i], arm_l = True, False
        if arm_s and zl[i] <= -2 and (not np.isfinite(prev) or prev > -2):
            short_sig[i], arm_s = True, False
    return pd.DataFrame({"p": p, "p4": p4, "z": z, "long_sig": long_sig, "short_sig": short_sig,
                         "u_missing": idx < first_u, "cb_ok": cb.notna(), "bn_ok": bn.notna(), "u_ok": u.notna()}, index=idx)


def selections(pr: pd.DataFrame, frames: dict) -> dict:
    """{coin: (long bool array, short bool array)} on each coin's own 1h index: the 10 most liquid eligible coins."""
    sig_t = pr.index[pr["long_sig"] | pr["short_sig"]]
    qv = {}
    elig = {}
    for coin, df in frames.items():
        d = df.set_index("date")
        qv[coin] = (d["qvol"].rolling(24, min_periods=24).sum()).reindex(sig_t)
        elig[coin] = pd.Series(T.eligible(df, 24) & ~np.isnan(T.atr(df)), index=d.index).reindex(sig_t).fillna(False)
    qv, elig = pd.DataFrame(qv), pd.DataFrame(elig).astype(bool)
    chosen = qv.where(elig).rank(axis=1, ascending=False, method="first") <= 10
    out = {}
    for coin, df in frames.items():
        pos = pd.Index(df["date"]).get_indexer(sig_t)
        l_, s_ = np.zeros(len(df), bool), np.zeros(len(df), bool)
        for k, t in enumerate(sig_t):
            if pos[k] < 0 or not chosen.at[t, coin]:
                continue
            if pr.at[t, "long_sig"]:
                l_[pos[k]] = True
            if pr.at[t, "short_sig"]:
                s_[pos[k]] = True
        out[coin] = (l_, s_)
    return out


def twins(df: pd.DataFrame, tr: list[dict], rng) -> np.ndarray:
    if not tr:
        return np.zeros(REPS)
    o, c = df["open"].to_numpy(), df["close"].to_numpy()
    d = df["date"]
    pool = np.where((d >= pd.Timestamp(DEV[0], tz="UTC")) & (d < pd.Timestamp(DEV[1], tz="UTC")))[0]
    side = np.array([t["side"] for t in tr])
    b = np.array([t["bars"] for t in tr])
    pool = pool[pool + b.max() < len(c)]
    cost = 2 * (T.FEE + T.SLIP)
    out = np.zeros(REPS)
    for r in range(REPS):
        e = pool[(rng.random(len(b)) * len(pool)).astype(int)]
        out[r] = np.nansum(side * (c[e + b - 1] / o[e] - 1) - cost)
    return out


def generate() -> dict:
    pr = premium()
    OUT.mkdir(parents=True, exist_ok=True)
    frames = {c: bars(c, "1h") for c in coins()}
    frames = {c: df[df["date"] < END].reset_index(drop=True) for c, df in frames.items()}
    sel = selections(pr, frames)
    for i, (coin, df) in enumerate(frames.items()):
        l_, s_ = sel[coin]
        a = T.atr(df)
        tr = T.simulate(df, l_, s_, T.Exit(2.0, 3.0, 24), a, 24)
        tr2 = {t["entry_i"]: t for t in T.simulate(df, l_, s_, T.Exit(2.0, 3.0, 24), a, 24, cost_mult=2.0)}
        for t in tr:
            t["ret_x2"] = tr2[t["entry_i"]]["ret"]
            t["cost"] = 2 * (T.FEE + T.SLIP) + (T.STOP_EXTRA if t["reason"] == "stop" else 0.0)
            t["family"], t["coin"] = "C46", coin
        dev = [t for t in tr if utc(t["entry_t"]) < pd.Timestamp(DEV[1], tz="UTC")]
        tw = twins(df, dev, np.random.default_rng([i, 46]))
        res = pd.DataFrame(tr)
        if len(res):
            res = res.drop(columns=["entry_i", "exit_i"])
        res.to_parquet(OUT / f"{coin}.parquet")
        np.savez(OUT / f"{coin}.twins.npz", C46=tw)
    yrs = pr.index.year
    return {"signals_per_year": {str(y): {"long": int(pr["long_sig"][yrs == y].sum()), "short": int(pr["short_sig"][yrs == y].sum())}
                                 for y in sorted(set(yrs))},
            "coverage": {"hours": int(len(pr)), "premium_ok": int(pr["p"].notna().sum()), "cb_missing": int((~pr["cb_ok"]).sum()),
                         "bn_missing": int((~pr["bn_ok"]).sum()), "usdt_set_1": int(pr["u_missing"].sum()),
                         "usdt_missing_after_listing": int((~pr["u_ok"]).sum())},
            "premium_pct": {"median": round(float(pr["p"].median() * 100), 4), "p1": round(float(pr["p"].quantile(0.01) * 100), 4),
                            "p99": round(float(pr["p"].quantile(0.99) * 100), 4)}}


def load(a: str, b: str) -> tuple[pd.DataFrame, np.ndarray]:
    parts, tw = [], np.zeros(REPS)
    lo, hi = pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC")
    for f in sorted(OUT.glob("*.parquet")):
        x = pd.read_parquet(f)
        if len(x):
            for col in ("entry_t", "exit_t"):
                x[col] = pd.to_datetime(x[col], utc=True)
            parts.append(x[(x["entry_t"] >= lo) & (x["entry_t"] < hi)])
        z = OUT / f"{f.stem}.twins.npz"
        if z.exists():
            tw = tw + np.load(z)["C46"]
    return pd.concat(parts, ignore_index=True), tw


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["dev", "valid", "wf"])
    a = ap.parse_args()
    mn = mins()
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = [json.loads(l) for l in open(RUNS / "ledger_c.jsonl", encoding="utf-8")]
    has = lambda stage, v: any(r["family"] == "C46" and r["stage"] == stage and r["verdict"] == v for r in rows)
    info = {}
    if a.stage == "dev":
        info = generate()
        per = PERIODS["1h"]["dev"]
        t, tw = load(per[0][1], per[-1][2])
        r = evaluate("C46", t, per, mn, tw)
        m = r["book"]
        pg, pg_name = period_gate("C46", r, 0.75, 2, 3)
        g = {"≥200 trades": m.get("trades", 0) >= 200, "PF ≥ 1.15": m.get("pf", 0) >= 1.15,
             "PF ≥ 1.0 at 2x costs": r["book_x2"].get("pf", 0) >= 1.0, "DD ≤ 35%": m.get("max_dd_pct", 100) <= 35,
             pg_name: pg, "beats 95% of random twins": r.get("twin_pct", 0) >= 95,
             "top coin ≤ 20% of profit": (m.get("top_coin_share") or 1) <= 0.20}
        verdict = "PASS DEV" if all(g.values()) else "FAIL DEV"
    elif a.stage == "valid":
        if not has("dev", "PASS DEV"):
            raise SystemExit("no DEV pass recorded - VALID refused")
        per = PERIODS["1h"]["valid"]
        t, _ = load(per[0][1], per[-1][2])
        r = evaluate("C46", t, per, mn, None)
        m = r["book"]
        g = {"PF ≥ 1.10": m["pf"] >= 1.10, "profit": m["final"] > 300, "profit at 2x costs": r["book_x2"]["final"] > 300,
             "DD ≤ 40%": m["max_dd_pct"] <= 40}
        verdict = "PASS VALID" if all(g.values()) else "FAIL VALID"
    else:
        if not has("valid", "PASS VALID"):
            raise SystemExit("no VALID pass recorded - WALK-FORWARD refused")
        periods, need = WALK_FORWARD["1h"]
        t, _ = load(periods[0][1], periods[-1][2])
        r = evaluate("C46", t, periods, mn, None)
        pg, pg_name = period_gate("C46", r, 5 / 8, 3, need)
        g = {pg_name: pg}
        verdict = "PASS WALK-FORWARD" if pg else "FAIL WALK-FORWARD"
    r["data"] = info
    ledger({"at": stamp, "batch": "C46", "family": "C46", "tf": "1h", "stage": a.stage, "result": r, "gates": g,
            "verdict": verdict})
    keys = ("book", "book_x2", "periods_detail", "by_cell", "all_signals", "twin_pct", "data")
    print(json.dumps({k: r.get(k) for k in keys} | {"gates": g}, indent=1, default=str))
    print("VERDICT: C46", verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
