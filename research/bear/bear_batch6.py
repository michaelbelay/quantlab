"""Bear batch 6 (D1-D6), step 1 with A2 robustness gates, step 2 for passers. Register: REGISTER_BEAR_IDEAS_2026-11-01_batch6.md.

    .venv\\Scripts\\python.exe research\\bear\\bear_batch6.py

Output: research/bear/batch6/trades_<idea>.csv, report.json. Nothing here is tuned after the run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bear_batch5 as b5  # noqa: E402
import bear_gates as bg  # noqa: E402

OUT = HERE / "batch6"
COINS, H, C, N, IDX = b5.COINS, b5.H, b5.C, b5.N, b5.IDX
CL, HI, LO, CF = b5.CL, b5.HI, b5.LO, b5.CF
EL = b5.ELIG.to_numpy()
BEAR_NEXT, DAILY = b5.BEAR_NEXT, b5.DAILY
COST = b5.COST
NC = len(COINS)


def deep_next() -> np.ndarray:
    """deep bear known at each bar's close (for the next bar): BTC daily close < SMA200 and SMA200 below 20 days ago."""
    spot = pd.read_feather(b5.ROOT / "data" / "market" / "dev_1h" / "binance" / "BTC_USDT-1d.feather").set_index("date").close
    spot.index = pd.to_datetime(spot.index, utc=True) + pd.Timedelta(days=1)       # close of day D, known at D+1 00:00
    btc = C["BTC"]
    fut = btc[btc.index.hour == 23]
    fut.index = fut.index.normalize() + pd.Timedelta(days=1)
    dc = pd.concat([spot[spot.index < fut.index[0]], fut]).sort_index()
    sma = dc.rolling(200).mean()
    deep = (dc < sma) & (sma < sma.shift(20))
    day = pd.Series(H.normalize().map(deep).fillna(False).astype(bool).to_numpy(), index=H)
    return day.shift(-1, fill_value=False).to_numpy()


def single_path(k, i, j, side, px):
    p = side * (CL[i:j + 1, k] / CL[i, k] - 1) - side * (CF[i:j + 1, k] - CF[i, k])
    p[-1] = side * (px / CL[i, k] - 1) - side * (CF[j, k] - CF[i, k])
    return p


def run_single(sig, side, stop, hold=None, exit_masks=None):
    """sig, exit_masks: (N, NC) bool. Returns trades and their paths for step 2."""
    rows, paths = [], []
    s = sig & EL
    for c in COINS:
        k = IDX[c]
        busy = -1
        for i in np.flatnonzero(s[:, k]):
            if i <= busy:
                continue
            t = b5.single(k, i, side, stop, hold, None if exit_masks is None else exit_masks[:, k])
            if not t:
                continue
            j = t[0]
            busy = j
            g = t[1] + COST
            px = CL[i, k] * (1 + g / side + (CF[j, k] - CF[i, k]))        # back out the exit price
            rows.append((c, H[i], H[j], t[1], t[2]))
            paths.append((i, single_path(k, i, j, side, px)))
    return pd.DataFrame(rows, columns=["coin", "entry", "exit", "net", "net2x"]), paths


def run_pairs(events, stop, hold):
    """events: list of (i, short k, long k). One pair per (short coin) at a time."""
    rows, paths = [], []
    busy = {}
    for i, ks, kl in events:
        if busy.get(ks, -1) >= i or busy.get(kl, -1) >= i:
            continue
        t = b5.pair(ks, kl, i, stop, hold)
        if not t:
            continue
        j = t[0]
        busy[ks] = busy[kl] = j
        p = np.array([b5.leg(ks, i, x, -1) + b5.leg(kl, i, x, 1) for x in range(i, j + 1)])
        rows.append((f"{COINS[ks]}/{COINS[kl]}", H[i], H[j], t[1], t[2], b5.leg(ks, i, j, -1) - COST))
        paths.append((i, p))
    return pd.DataFrame(rows, columns=["coin", "entry", "exit", "net", "net2x", "short_leg"]), paths


def daily_panel(n_days):
    """per-coin daily-close moving average (value at the 23:00 bar, forward-filled within the day)."""
    d = C[DAILY]
    return d.rolling(n_days, min_periods=n_days).mean().reindex(H).ffill()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    DEEP = deep_next()
    bear = np.repeat(BEAR_NEXT[:, None], NC, 1)
    deep = np.repeat((DEEP & BEAR_NEXT)[:, None], NC, 1)
    daily = np.repeat(DAILY[:, None], NC, 1)
    R, P = {}, {}

    e480 = b5.bx.ema(480)
    cross = ((C < e480) & (C.shift(1) >= e480.shift(1))).to_numpy()
    R["D1_deep_trend_break"], P["D1_deep_trend_break"] = run_single(cross & deep, -1, 0.06, hold=168)

    sma50d = daily_panel(50)
    dcl = C.where(np.repeat(DAILY[:, None], NC, 1))
    below = (dcl < sma50d).to_numpy() & (sma50d < sma50d.shift(5 * 24)).to_numpy()
    ex = daily & (((dcl > sma50d).to_numpy()) | ~np.repeat(DEEP[:, None], NC, 1))
    R["D2_deep_below_50d"], P["D2_deep_below_50d"] = run_single(below & deep & daily, -1, 0.12, exit_masks=ex)

    r72 = (C / C.shift(72) - 1).to_numpy()
    ev = []
    for i in np.flatnonzero(DAILY & BEAR_NEXT):
        idx = np.flatnonzero(EL[i] & ~np.isnan(r72[i]))
        if len(idx) < 6:
            continue
        o = idx[np.argsort(r72[i, idx])]
        ev += [(i, hi_, lo_) for hi_, lo_ in zip(o[::-1][:3], o[:3])]
    R["D3_xs_reversal_pair"], P["D3_xs_reversal_pair"] = run_pairs(ev, 0.15, 72)

    fa = b5.FUND_AT.to_numpy()
    ev = []
    for i in np.flatnonzero(np.asarray(H.hour == 23) & BEAR_NEXT):
        idx = np.flatnonzero(EL[i] & ~np.isnan(fa[i]))
        if len(idx) < 6:
            continue
        o = idx[np.argsort(fa[i, idx])]
        ev += [(i, hi_, lo_) for hi_, lo_ in zip(o[::-1][:3], o[:3])]
    R["D4_funding_xs_pair"], P["D4_funding_xs_pair"] = run_pairs(ev, 0.15, 72)

    ratio = C.div(C["BTC"], axis=0)
    rd = ratio[DAILY]
    ra = rd.rolling(30, min_periods=30).mean()
    cr = (rd < ra) & (rd.shift(1) >= ra.shift(1))
    first = cr & ~cr.shift(1).rolling(7, min_periods=1).max().fillna(0).astype(bool)
    first = first.reindex(H).fillna(False).to_numpy()
    kb = IDX["BTC"]
    ev = [(i, k, kb) for i, k in zip(*np.nonzero(first & bear & EL)) if k != kb and EL[i, kb]]
    ev.sort()
    R["D5_alt_vs_btc_trend"], P["D5_alt_vs_btc_trend"] = run_pairs(ev, 0.12, 168)

    sma50h = C.rolling(1200, min_periods=1200).mean()
    d6 = (r72 >= 0.10) & (C < sma50h).to_numpy()
    R["D6_deep_rally_short"], P["D6_deep_rally_short"] = run_single(d6 & deep, -1, 0.08, hold=72)

    rep = {}
    for k, tr in R.items():
        tr.sort_values("net").to_csv(OUT / f"trades_{k}.csv", index=False)
        rep[k] = bg.stats(tr)
        if rep[k]["verdict"] == "🟠":
            pair = "short_leg" in tr
            s1 = bg.step2(P[k], N, H, (2 if pair else 1) * COST, 1, legs_per_trade=2 if pair else 1)
            s2 = bg.step2(P[k], N, H, (2 if pair else 1) * COST, 2, legs_per_trade=2 if pair else 1)
            ok = s1["profit_usdt"] > 0 and s2["profit_usdt"] > 0 and s1["max_dd_pct"] >= -35 and s1["worst_trade_usdt"] >= -30
            rep[k]["step2"], rep[k]["step2_2x"] = s1, s2
            rep[k]["verdict"] = "🟡" if ok else "🟠"
        print(k, json.dumps(rep[k], ensure_ascii=False))
    (OUT / "report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
