"""Bear batch 9 (L1-L3), shallow-bear longs with a crash guard. Register: REGISTER_BEAR_IDEAS_2026-11-01_batch9.md.

    .venv\\Scripts\\python.exe research\\bear\\bear_batch9.py

Output: research/bear/batch9/trades_<idea>.csv, report.json. Nothing here is tuned after the run.
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

OUT = HERE / "batch9"
COINS, H, C, N, IDX, NC = b5.COINS, b5.H, b5.C, b5.N, b5.IDX, b6.NC
EL, COST, DAILY = b6.EL, b5.COST, b5.DAILY


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    DEEP = b6.deep_next()
    shallow = DAILY & b5.BEAR_NEXT & ~DEEP
    sh = np.repeat(shallow[:, None], NC, 1)
    guard = np.repeat((DAILY & DEEP)[:, None], NC, 1)          # crash guard exit
    R, P = {}, {}

    sma50 = b6.daily_panel(50)
    r7 = (C / C.shift(168) - 1).to_numpy()
    l1 = sh & (C > sma50).to_numpy() & (r7 <= 0)
    R["L1_uptrend_dip"], P["L1_uptrend_dip"] = b6.run_single(l1, 1, 0.10, hold=168, exit_masks=guard)

    l2 = np.zeros((N, NC), bool)
    for c in ("BTC", "ETH"):
        l2[:, IDX[c]] = shallow
    R["L2_majors_dip"], P["L2_majors_dip"] = b6.run_single(l2, 1, 0.08, hold=168, exit_masks=guard)

    r30 = (C / C.shift(720) - 1).to_numpy()
    l3 = np.zeros((N, NC), bool)
    for i in np.flatnonzero(shallow & np.asarray(H.dayofweek == 6)):
        idx = np.flatnonzero(EL[i] & ~np.isnan(r30[i]))
        if len(idx) >= 3:
            l3[i, idx[np.argsort(r30[i, idx])][-3:]] = True
    R["L3_leaders_hold"], P["L3_leaders_hold"] = b6.run_single(l3, 1, 0.12, hold=168, exit_masks=guard)

    rep = {}
    for k, tr in R.items():
        tr.sort_values("net").to_csv(OUT / f"trades_{k}.csv", index=False)
        rep[k] = bg.stats(tr)
        wk = tr.groupby(tr.entry.dt.to_period("W")).net.sum()
        rep[k]["worst_week_sum_pct"] = [str(wk.idxmin()), round(100 * wk.min(), 1)] if len(wk) else None
        if rep[k]["verdict"] == "🟠":
            s1, s2 = bg.step2(P[k], N, H, COST, 1), bg.step2(P[k], N, H, COST, 2)
            rep[k]["step2"], rep[k]["step2_2x"] = s1, s2
            rep[k]["verdict"] = "🟡" if (s1["profit_usdt"] > 0 and s2["profit_usdt"] > 0 and s1["max_dd_pct"] >= -35
                                        and s1["worst_trade_usdt"] >= -30) else "🟠"
        print(k, json.dumps(rep[k], ensure_ascii=False))
    (OUT / "report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
