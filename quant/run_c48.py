r"""C48 Meme crowd impulse (FAMILIES_C.md "C48", registered 2026-10-19 before this file existed).

    .venv\Scripts\python.exe -m quant.run_c48 dev      # download 15m + funding, generate trades, judge DEV only
    .venv\Scripts\python.exe -m quant.run_c48 valid    # refused without a recorded DEV pass
    .venv\Scripts\python.exe -m quant.run_c48 wf       # refused without a recorded VALID pass

Long only on 25 meme coins. Signal at a 15m close: quote volume AND number of trades >= 3x their 96-bar mean, close
above the 96-bar high, green bar, PROTOCOL_C eligibility. Entry next open. Exits: safety stop = signal-bar low,
trailing stop = highest high since entry - 3 ATR14, "crowd leaves" (4-bar mean volume < baseline, from the 4th bar),
time 96 bars. Costs: fee 0.05% + slippage 0.10% per side, stop +0.05%, real funding.
Data cache: data/c48. Trades -> runs/c_trades/C48/15m/<coin>.parquet; results -> runs/ledger_c.jsonl.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import trades as T
from .eval_c import PERIODS, WALK_FORWARD, ledger, mins
from .paths import DATA, RUNS
from .run_c42_c43 import REPS, evaluate, period_gate

COINS = ["DOGE", "1000PEPE", "PUMP", "TRUMP", "PENGU", "FARTCOIN", "1000SHIB", "WIF", "1000BONK", "BOME", "SPX", "NEIRO",
         "PNUT", "1000FLOKI", "TURBO", "PEOPLE", "1000RATS", "GIGGLE", "USELESS", "MUBARAK", "ZEREBRO", "TUT",
         "龙虾", "牛来", "币安人生"]
MONTHS = [str(p) for p in pd.period_range("2024-08", "2026-03", freq="M")]
KURL = "https://data.binance.vision/data/futures/um/monthly/klines/{s}/15m/{s}-15m-{m}.zip"
FURL = "https://data.binance.vision/data/futures/um/monthly/fundingRate/{s}/{s}-fundingRate-{m}.zip"
CACHE = DATA / "c48"
OUT = RUNS / "c_trades" / "C48" / "15m"
SPLIT = {"dev": ("2024-09-01", "2025-09-01"), "valid": ("2025-09-01", "2026-03-26")}
BASE, MULT, K_TRAIL, FADE_FROM, HOLD = 96, 3.0, 3.0, 4, 96
SLIP_MEME = 0.0010                                   # registered: memes are thin, slippage 0.10% per side
FAM, BPD, BAR_MIN, TF = "C48", 96, 15, "15m"      # C49 (1h) overrides these


def _zip_csv(url: str) -> pd.DataFrame | None:
    try:
        raw = urllib.request.urlopen(url, timeout=120).read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        return pd.read_csv(z.open(z.namelist()[0]), header=None)


def fetch(coin: str) -> tuple[pd.DataFrame, pd.Series]:
    fk, ff = CACHE / f"{coin}.parquet", CACHE / f"{coin}.funding.parquet"
    if fk.exists() and ff.exists():
        f = pd.read_parquet(ff)
        return pd.read_parquet(fk), pd.Series(f["rate"].to_numpy(), index=pd.DatetimeIndex(f["t"]))
    s = urllib.parse.quote(f"{coin}USDT")
    kp, fp = [], []
    for m in MONTHS:
        k = _zip_csv(KURL.format(s=s, m=m))
        if k is not None:
            k = k[pd.to_numeric(k[0], errors="coerce").notna()].iloc[:, [0, 1, 2, 3, 4, 7, 8]].astype(float)
            k.columns = ["t", "open", "high", "low", "close", "qvol", "count"]
            kp.append(k)
        f = _zip_csv(FURL.format(s=s, m=m))
        if f is not None:
            f = f[pd.to_numeric(f[0], errors="coerce").notna()]
            fp.append(pd.DataFrame({"t": pd.to_datetime(f[0].astype("int64"), unit="ms"), "rate": f[2].astype(float)}))
    cols = ["t", "open", "high", "low", "close", "qvol", "count"]
    d = pd.concat(kp, ignore_index=True) if kp else pd.DataFrame(columns=cols)
    d = d.drop_duplicates("t").sort_values("t").reset_index(drop=True)
    d["date"] = pd.to_datetime(d["t"].astype("int64"), unit="ms")
    d = d.drop(columns="t")
    fu = pd.concat(fp, ignore_index=True).drop_duplicates("t").sort_values("t") if fp else pd.DataFrame(columns=["t", "rate"])
    CACHE.mkdir(parents=True, exist_ok=True)
    d.to_parquet(fk)
    fu.to_parquet(ff)
    return d, pd.Series(fu["rate"].to_numpy(dtype=float), index=pd.DatetimeIndex(fu["t"]))


def grid(d: pd.DataFrame) -> pd.DataFrame:
    """Put bars on a full 15m grid (missing bars = NaN), so 96 bars always means 24 h."""
    if not len(d):
        return d
    g = pd.date_range(d["date"].iloc[0], d["date"].iloc[-1], freq=f"{BAR_MIN}min")
    return d.set_index("date").reindex(g).rename_axis("date").reset_index()


def signals(d: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    o, h, l, c = (d[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    qv, cnt = d["qvol"].to_numpy(dtype=float), d["count"].to_numpy(dtype=float)
    prev = lambda x, f: getattr(pd.Series(x).rolling(BASE, min_periods=BASE), f)().shift(1).to_numpy()
    base_qv, base_cnt, hi96 = prev(qv, "mean"), prev(cnt, "mean"), prev(h, "max")
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.c_[h - l, np.abs(h - pc), np.abs(l - pc)], axis=1)
    atr = pd.Series(tr).rolling(14, min_periods=14).mean().to_numpy()
    qv24 = pd.Series(qv).rolling(BASE, min_periods=BASE).sum().shift(1).to_numpy()
    listed = np.arange(len(d)) >= T.MIN_LISTED_DAYS * BPD
    with np.errstate(invalid="ignore"):
        sig = ((qv >= MULT * base_qv) & (cnt >= MULT * base_cnt) & (c > hi96) & (c > o)
               & listed & (qv24 >= T.MIN_QVOL_24H) & np.isfinite(atr))
    return sig, base_qv, atr


def c48_trades(d: pd.DataFrame, fu: pd.Series, cost_mult: float = 1.0) -> list[dict]:
    o, h, l, c = (d[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    qv = d["qvol"].to_numpy(dtype=float)
    dates = d["date"].to_numpy()
    sig, base_qv, atr = signals(d)
    side_cost = (T.FEE + SLIP_MEME) * cost_mult
    sx = T.STOP_EXTRA * cost_mult
    out, free, n = [], 0, len(d)
    for s in np.where(sig)[0]:
        e = s + 1
        if s < free or e + HOLD >= n or not np.all(np.isfinite(c[e:e + HOLD])):
            continue
        px = o[e]
        safety = l[s]
        if not np.isfinite(px) or px <= safety:
            continue
        a = atr[s]
        peak = -np.inf
        x, reason, xp = e + HOLD - 1, "time", c[e + HOLD - 1]
        for j in range(e, e + HOLD):
            stop = max(safety, peak - K_TRAIL * a)          # peak from bars BEFORE j only (pessimistic)
            if l[j] <= stop:
                xp = (o[j] if o[j] < stop else stop) * (1 - sx)
                x, reason = j, ("trail" if stop > safety else "stop")
                break
            peak = max(peak, h[j])
            if j - e + 1 >= FADE_FROM and np.mean(qv[j - 3:j + 1]) < base_qv[s] and j + 1 < n:
                x, reason, xp = j + 1, "fade", o[j + 1]          # exit at the next open
                break
        gross = xp / px - 1
        et, xt = pd.Timestamp(dates[e]), pd.Timestamp(dates[x]) + pd.Timedelta(minutes=BAR_MIN)
        f = float(fu[(fu.index > et) & (fu.index <= xt)].sum()) if len(fu) else 0.0       # longs pay +funding
        hi_after = np.nanmax(h[e:x + 1])
        out.append({"entry_i": e, "exit_i": x, "side": 1, "entry_t": dates[e], "exit_t": dates[x],
                    "ret": gross - 2 * side_cost - f, "gross": gross, "funding": f, "reason": reason,
                    "mae": float(np.nanmin(l[e:x + 1]) / px - 1), "bars": x - e + 1,
                    "cost": 2 * side_cost + (sx if reason in ("stop", "trail") else 0.0),
                    "late": bool(hi_after < px + a), "atr_pct": float(a / px)})
        free = x + 1
    return out


def twins(d: pd.DataFrame, tr: list[dict], lo: str, hi: str, rng) -> np.ndarray:
    """Same coin, long, same holding bars and cost, entered at a random eligible 15m open in the split."""
    if not tr:
        return np.zeros(REPS)
    o, c = d["open"].to_numpy(dtype=float), d["close"].to_numpy(dtype=float)
    qv = d["qvol"].to_numpy(dtype=float)
    qv24 = pd.Series(qv).rolling(BASE, min_periods=BASE).sum().shift(1).to_numpy()
    dt = d["date"].to_numpy()
    ok = (np.arange(len(d)) >= T.MIN_LISTED_DAYS * BPD) & (qv24 >= T.MIN_QVOL_24H) & np.isfinite(o)
    pool = np.where(ok & (dt >= np.datetime64(lo)) & (dt < np.datetime64(hi)))[0]
    b = np.array([t["bars"] for t in tr])
    cost = np.array([t["cost"] for t in tr])
    pool = pool[pool + b.max() < len(c)]
    out = np.zeros(REPS)
    for r in range(REPS):
        e = pool[(rng.random(len(b)) * len(pool)).astype(int)]
        out[r] = np.nansum(c[e + b - 1] / o[e] - 1 - cost)
    return out


def generate(split: str) -> tuple[pd.DataFrame, np.ndarray, dict]:
    lo, hi = SPLIT[split]
    rows, tw, data = [], np.zeros(REPS), {}
    OUT.mkdir(parents=True, exist_ok=True)
    for i, coin in enumerate(COINS):
        raw, fu = fetch(coin)
        d = grid(raw)
        data[coin] = {"bars": int(len(raw)), "first": str(raw["date"].iloc[0]) if len(raw) else None,
                      "missing_bars": int(d["close"].isna().sum()) if len(d) else 0, "funding_events": int(len(fu))}
        if not len(d):
            print(f"  {FAM} {coin}: no data in range", flush=True)
            continue
        tr = c48_trades(d, fu)
        x2 = {t["entry_i"]: t for t in c48_trades(d, fu, 2.0)}
        for t in tr:
            t2 = x2.get(t["entry_i"])
            t["ret_x2"] = t2["ret"] if t2 is not None else t["ret"] - t["cost"]
            t["family"], t["coin"] = FAM, coin
        pd.DataFrame(tr).to_parquet(OUT / f"{coin}.parquet")
        sel = [t for t in tr if np.datetime64(lo) <= t["entry_t"] < np.datetime64(hi)]
        tw = tw + twins(d, sel, lo, hi, np.random.default_rng([i, int(FAM[1:]), 0 if split == "dev" else 1]))
        rows += sel
        print(f"  {FAM} {coin}: {len(tr)} trades all periods, {len(sel)} in {split}", flush=True)
    t = pd.DataFrame(rows)
    if len(t):
        t = t.drop(columns=["entry_i", "exit_i"])
        for col in ("entry_t", "exit_t"):
            t[col] = pd.to_datetime(t[col], utc=True)
    return t, tw, data


def extras(t: pd.DataFrame) -> dict:
    pf = lambda x: round(float(x[x > 0].sum() / max(1e-9, -x[x < 0].sum())), 3)
    day = t["entry_t"].dt.floor("D")
    top3 = t.groupby(day)["ret"].sum().nlargest(3).index
    rest = t[~day.isin(top3)]
    per_coin = {c: {"trades": int(len(g)), "sum_ret_pct": round(float(g["ret"].sum() * 100), 1), "pf": pf(g["ret"])}
                for c, g in t.groupby("coin")}
    return {"per_coin": per_coin, "late_entry_share": round(float(t["late"].mean()), 3),
            "pf_without_top3_days": pf(rest["ret"]), "top3_days": [str(x.date()) for x in top3],
            "avg_win_pct": round(float(t.loc[t.ret > 0, "ret"].mean() * 100), 2),
            "avg_loss_pct": round(float(t.loc[t.ret <= 0, "ret"].mean() * 100), 2),
            "win_rate": round(float((t.ret > 0).mean()), 3), "median_bars": float(t["bars"].median()),
            "avg_atr_pct": round(float(t["atr_pct"].mean() * 100), 2)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["dev", "valid", "wf"])
    ap.add_argument("--override", default="", help="recorded reason when a gate is overridden by Michael")
    a = ap.parse_args()
    mn = mins()
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = [json.loads(x) for x in open(RUNS / "ledger_c.jsonl", encoding="utf-8")]
    has = lambda stage, v: any(r["family"] == FAM and r["stage"] == stage and r["verdict"] == v for r in rows)
    if a.stage == "dev":
        t, tw, data = generate("dev")
        r = evaluate(FAM, t, PERIODS["intra"]["dev"], mn, tw)
        m = r["book"]
        pg, pg_name = period_gate(FAM, r, 0.75, 3, 3)
        g = {"≥200 trades": m.get("trades", 0) >= 200, "PF ≥ 1.15": m.get("pf", 0) >= 1.15,
             "PF ≥ 1.0 at 2x costs": r["book_x2"].get("pf", 0) >= 1.0, "DD ≤ 35%": m.get("max_dd_pct", 100) <= 35,
             pg_name: pg, "beats 95% of random twins": r.get("twin_pct", 0) >= 95,
             "top coin ≤ 20% of profit": (m.get("top_coin_share") or 1) <= 0.20}
        verdict = "PASS DEV" if all(g.values()) else "FAIL DEV"
        r["data"] = data
    elif a.stage == "valid":
        if not has("dev", "PASS DEV") and not a.override:
            raise SystemExit("no DEV pass recorded - VALID refused")
        t, tw, _ = generate("valid")
        r = evaluate(FAM, t, PERIODS["intra"]["valid"], mn, tw)
        m = r["book"]
        g = {"PF ≥ 1.10": m["pf"] >= 1.10, "profit": m["final"] > 300, "profit at 2x costs": r["book_x2"]["final"] > 300,
             "DD ≤ 40%": m["max_dd_pct"] <= 40}
        verdict = "PASS VALID" if all(g.values()) else "FAIL VALID"
    else:
        if not has("valid", "PASS VALID"):
            raise SystemExit("no VALID pass recorded - WALK-FORWARD refused")
        raise SystemExit("walk-forward not built yet: build it only after a VALID pass")
    r["extras"] = extras(t)
    ledger({"at": stamp, "batch": FAM, "family": FAM, "tf": TF, "stage": a.stage, "result": r, "gates": g,
            "verdict": verdict} | ({"override": a.override} if a.override else {}))
    keys = ("book", "book_x2", "book_lev2", "periods_detail", "by_cell", "all_signals", "extras", "twin_pct", "data")
    print(json.dumps({k: r.get(k) for k in keys} | {"gates": g}, indent=1, default=str, ensure_ascii=False))
    print("VERDICT:", FAM, verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
