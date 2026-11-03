"""Bear batch 8 (H1-H4), intraday breakdown shorts. Register: REGISTER_BEAR_IDEAS_2026-11-01_batch8.md.

    .venv\\Scripts\\python.exe research\\bear\\bear_batch8.py

Output: research/bear/batch8/trades_<idea>.csv, report.json. Nothing here is tuned after the run.
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

OUT = HERE / "batch8"
COINS, H, N, IDX = b5.COINS, b5.H, b5.N, b5.IDX
CL, HI, LO, CF, EL = b5.CL, b5.HI, b5.LO, b5.CF, b6.EL
OP = b5.bx.O.to_numpy()
COST = b5.COST


def day_short(k, d0, first, trig, stop):
    """stop-entry short inside day d0..d0+23, searching from bar `first`; exit 23:00 close."""
    end = d0 + 23
    if end >= N or np.isnan(CL[end, k]):
        return None
    for i in range(first, end + 1):
        if np.isnan(LO[i, k]):
            return None
        if LO[i, k] <= trig:
            break
    else:
        return None
    e = min(trig, OP[i, k])
    if stop <= e:
        return None
    j, px = end, CL[end, k]
    for x in range(i, end + 1):
        if HI[x, k] >= stop:
            j, px = x, stop
            break
    base = CF[i - 1, k] if i > 0 else 0.0
    g = -(px / e - 1) + (CF[j, k] - base)
    path = -(CL[i:j + 1, k] / e - 1) + (CF[i:j + 1, k] - base)
    path[-1] = g
    return i, j, g - COST, g - 2 * COST, path


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    deep_day = np.concatenate([[False], b6.deep_next()[:-1]])
    bear_day = b5.BEAR_NOW
    dH, dL, dC = b5.bx.Hi.resample("D").max(), b5.bx.Lo.resample("D").min(), b5.bx.C.resample("D").last()
    tr_ = pd.concat([dH - dL, (dH - dC.shift(1)).abs(), (dL - dC.shift(1)).abs()]).groupby(level=0).max()
    atr = tr_.rolling(14, min_periods=14).mean().shift(1)
    pH, pL, pC = dH.shift(1), dL.shift(1), dC.shift(1)
    starts = np.flatnonzero(np.asarray(H.hour == 0))
    R = {n: [] for n in ("H1_open_break", "H2_open_break_deep", "H3_range_break", "H4_prev_low_break")}
    P = {n: [] for n in R}

    def add(name, c, t):
        if t:
            R[name].append((c, H[t[0]], H[t[1]], t[2], t[3]))
            P[name].append((t[0], t[4]))

    for d0 in starts:
        if not bear_day[d0]:
            continue
        day = H[d0].normalize()
        if day not in atr.index:
            continue
        for c in COINS:
            k = IDX[c]
            if not EL[d0, k] or d0 + 23 >= N:
                continue
            o, a = OP[d0, k], atr.at[day, c]
            if np.isnan(o) or np.isnan(a):
                continue
            t1 = day_short(k, d0, d0, o - 0.75 * a, o)
            add("H1_open_break", c, t1)
            if deep_day[d0]:
                add("H2_open_break_deep", c, t1)
            rl, rh = np.nanmin(LO[d0:d0 + 4, k]), np.nanmax(HI[d0:d0 + 4, k])
            if rh - rl < a:
                add("H3_range_break", c, day_short(k, d0, d0 + 4, rl, rh))
            pl, pc = pL.at[day, c], pC.at[day, c]
            if not np.isnan(pl) and o > pl:
                add("H4_prev_low_break", c, day_short(k, d0, d0, pl, pc))

    rep = {}
    for k, rows in R.items():
        tr = pd.DataFrame(rows, columns=["coin", "entry", "exit", "net", "net2x"])
        tr.sort_values("net").to_csv(OUT / f"trades_{k}.csv", index=False)
        rep[k] = bg.stats(tr)
        if rep[k]["verdict"] == "🟠":
            s1, s2 = bg.step2(P[k], N, H, COST, 1), bg.step2(P[k], N, H, COST, 2)
            rep[k]["step2"], rep[k]["step2_2x"] = s1, s2
            rep[k]["verdict"] = "🟡" if (s1["profit_usdt"] > 0 and s2["profit_usdt"] > 0 and s1["max_dd_pct"] >= -35
                                        and s1["worst_trade_usdt"] >= -30) else "🟠"
        print(k, json.dumps(rep[k], ensure_ascii=False))
    (OUT / "report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
