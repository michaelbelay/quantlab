"""Bear batch 7 (G1-G5), step 1 with A2 gates, step 2 for passers. Register: REGISTER_BEAR_IDEAS_2026-11-01_batch7.md.

    .venv\\Scripts\\python.exe research\\bear\\bear_batch7.py

Output: research/bear/batch7/trades_<idea>.csv, report.json. Nothing here is tuned after the run.
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
import bear_batch6 as b6  # noqa: E402
import bear_gates as bg  # noqa: E402

OUT = HERE / "batch7"
COINS, H, C, N, IDX, NC = b5.COINS, b5.H, b5.C, b5.N, b5.IDX, b6.NC
CL, HI, LO, CF, EL = b5.CL, b5.HI, b5.LO, b5.CF, b6.EL
OP = b5.bx.O.to_numpy()
BEAR_NEXT, BEAR_NOW, DAILY, COST = b5.BEAR_NEXT, b5.BEAR_NOW, b5.DAILY, b5.COST


def limit_day(k, d0, mult, smult, atr):
    """one day from bar d0 (00:00): limit short at open + mult*ATR, stop open + smult*ATR, exit at the 23:00 close."""
    o = OP[d0, k]
    if np.isnan(o) or np.isnan(atr) or d0 + 23 >= N:
        return None
    lim, sp = o + mult * atr, o + smult * atr
    for i in range(d0, d0 + 24):
        if np.isnan(HI[i, k]):
            return None
        if HI[i, k] >= lim:
            break
    else:
        return None
    j, px = d0 + 23, CL[d0 + 23, k]
    for x in range(i, d0 + 24):
        if HI[x, k] >= sp:
            j, px = x, sp
            break
    if np.isnan(px):
        return None
    fund = CF[j, k] - (CF[i - 1, k] if i > 0 else 0.0)
    g = -(px / lim - 1) + fund
    path = -(CL[i:j + 1, k] / lim - 1) + (CF[i:j + 1, k] - (CF[i - 1, k] if i > 0 else 0.0))
    path[-1] = g
    return i, j, g - COST, g - 2 * COST, path


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    DEEP = b6.deep_next()
    DB = DEEP & BEAR_NEXT
    deep = np.repeat(DB[:, None], NC, 1)
    daily = np.repeat(DAILY[:, None], NC, 1)
    R, P = {}, {}

    sma20 = b6.daily_panel(20)
    dcl = C.where(daily)
    g1 = daily & (dcl < sma20).to_numpy()
    ex = daily & ((dcl > sma20).to_numpy() | ~deep)
    R["G1_deep_trend_hold"], P["G1_deep_trend_hold"] = b6.run_single(g1 & deep, -1, 0.15, exit_masks=ex)

    r30 = (C / C.shift(720) - 1).to_numpy()
    g2 = np.zeros((N, NC), bool)
    for i in np.flatnonzero(DAILY & DB & np.asarray(H.dayofweek == 6)):
        idx = np.flatnonzero(EL[i] & ~np.isnan(r30[i]))
        if len(idx) >= 5:
            g2[i, idx[np.argsort(r30[i, idx])][:5]] = True
    R["G2_deep_weak_short"], P["G2_deep_weak_short"] = b6.run_single(g2, -1, 0.12, hold=168)

    # G3: rally (72h >= +8%) within the last 48h, then a close under the previous 12h low; stop = 72h high x 1.01
    r72 = C / C.shift(72) - 1
    rallied = (r72 >= 0.08).astype(float).rolling(48, min_periods=1).max().astype(bool).to_numpy()
    low12 = b5.bx.Lo.shift(1).rolling(12, min_periods=12).min().to_numpy()
    hi72 = b5.bx.Hi.rolling(72, min_periods=72).max().to_numpy()
    g3 = rallied & (CL < low12) & deep & EL
    rows, paths = [], []
    for c in COINS:
        k = IDX[c]
        busy = -1
        for i in np.flatnonzero(g3[:, k]):
            if i <= busy:
                continue
            stop = hi72[i, k] * 1.01 / CL[i, k] - 1
            t = b5.single(k, i, -1, stop, 72)
            if not t:
                continue
            j = busy = t[0]
            px = CL[i, k] * (1 + (t[1] + COST) / -1 + (CF[j, k] - CF[i, k]))
            rows.append((c, H[i], H[j], t[1], t[2]))
            paths.append((i, b6.single_path(k, i, j, -1, px)))
    R["G3_rally_break_deep"], P["G3_rally_break_deep"] = pd.DataFrame(rows, columns=["coin", "entry", "exit", "net", "net2x"]), paths

    # G4 / G5: intraday limit shorts above the open
    dH, dL, dC = (b5.bx.Hi.resample("D").max(), b5.bx.Lo.resample("D").min(), b5.bx.C.resample("D").last())
    tr_ = pd.concat([dH - dL, (dH - dC.shift(1)).abs(), (dL - dC.shift(1)).abs()]).groupby(level=0).max()
    atr = tr_.rolling(14, min_periods=14).mean().shift(1)            # last completed day
    starts = np.flatnonzero(np.asarray(H.hour == 0))
    bear_day = BEAR_NOW
    deep_day = np.concatenate([[False], DEEP[:-1]])                   # deep flag of the day this bar belongs to
    for name, mult, smult, need_deep in (("G4_spike_limit_short", 1.0, 2.0, False), ("G5_spike_limit_deep", 0.75, 1.75, True)):
        rows, paths = [], []
        for d0 in starts:
            if not bear_day[d0] or (need_deep and not deep_day[d0]):
                continue
            day = H[d0].normalize()
            for c in COINS:
                k = IDX[c]
                if not EL[d0, k] or day not in atr.index:
                    continue
                t = limit_day(k, d0, mult, smult, atr.at[day, c])
                if t:
                    rows.append((c, H[t[0]], H[t[1]], t[2], t[3]))
                    paths.append((t[0], t[4]))
        R[name], P[name] = pd.DataFrame(rows, columns=["coin", "entry", "exit", "net", "net2x"]), paths

    rep = {}
    for k, tr in R.items():
        tr.sort_values("net").to_csv(OUT / f"trades_{k}.csv", index=False)
        rep[k] = bg.stats(tr)
        if rep[k]["verdict"] == "🟠":
            s1 = bg.step2(P[k], N, H, COST, 1)
            s2 = bg.step2(P[k], N, H, COST, 2)
            ok = s1["profit_usdt"] > 0 and s2["profit_usdt"] > 0 and s1["max_dd_pct"] >= -35 and s1["worst_trade_usdt"] >= -30
            rep[k]["step2"], rep[k]["step2_2x"] = s1, s2
            rep[k]["verdict"] = "🟡" if ok else "🟠"
        print(k, json.dumps(rep[k], ensure_ascii=False))
    (OUT / "report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
