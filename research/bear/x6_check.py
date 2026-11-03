"""X6 xs_momentum_pair: report-only diagnostics + RULES_BEAR step 2 (300 USDT account, 6 slots = 3 pairs x 2 legs).

    .venv\\Scripts\\python.exe research\\bear\\x6_check.py

Step 2 sizing: 300 USDT, 1x, each leg 50 USDT (300 / 6 slots), equity marked to market every hour (open P&L included).
Output: research/bear/batch5/x6_check.json, x6_equity.csv. No rule of X6 is changed.
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

LEG = 50.0


def trades():
    """X6 trades again, with legs split (same rules as bear_batch5)."""
    el = b5.ELIG.to_numpy()
    r30 = (b5.C / b5.C.shift(720) - 1).to_numpy()
    rows = []
    for i in np.flatnonzero(b5.DAILY & b5.BEAR_NEXT & np.asarray(b5.H.dayofweek == 6)):
        idx = np.flatnonzero(el[i] & ~np.isnan(r30[i]))
        if len(idx) < 6:
            continue
        order = idx[np.argsort(r30[i, idx])]
        for w, s in zip(order[:3], order[::-1][:3]):
            t = b5.pair(w, s, i, 0.15, 168)
            if t:
                j = t[0]
                rows.append({"short": b5.COINS[w], "long": b5.COINS[s], "i": i, "j": j, "entry": b5.H[i],
                             "short_leg": b5.leg(w, i, j, -1), "long_leg": b5.leg(s, i, j, 1),
                             "net": t[1], "net2x": t[2]})
    return pd.DataFrame(rows)


def equity(tr, cost_mult):
    """hourly mark-to-market equity of the 300 USDT account."""
    pnl = np.zeros(b5.N)
    for r in tr.itertuples():
        ks, kl = b5.IDX[r.short], b5.IDX[r.long]
        path = np.array([b5.leg(ks, r.i, t, -1) + b5.leg(kl, r.i, t, 1) for t in range(r.i, r.j + 1)])
        path = LEG * (path - 2 * b5.COST * cost_mult)
        pnl[r.i:r.j + 1] += path
        pnl[r.j + 1:] += path[-1]
    eq = pd.Series(300 + pnl, index=b5.H)
    dd = (eq / eq.cummax() - 1).min()
    return eq, float(eq.iloc[-1] - 300), float(100 * dd)


def main():
    tr = trades()
    out = {"trades": len(tr),
           "avg_short_leg_pct": round(100 * tr.short_leg.mean(), 3), "avg_long_leg_pct": round(100 * tr.long_leg.mean(), 3),
           "short_leg_by_year": {str(y): round(100 * g.short_leg.mean(), 2) for y, g in tr.groupby(tr.entry.dt.year)},
           "long_leg_by_year": {str(y): round(100 * g.long_leg.mean(), 2) for y, g in tr.groupby(tr.entry.dt.year)}}
    m = tr.groupby(tr.entry.dt.strftime("%Y-%m")).net.sum().sort_values()
    out["top3_months_share_of_profit_pct"] = round(100 * m.tail(3).sum() / tr.net.sum(), 1)
    out["top3_months"] = {k: round(100 * v, 1) for k, v in m.tail(3).items()}
    out["avg_without_top10_trades"] = round(100 * tr.net.sort_values().iloc[:-10].mean(), 3)
    out["worst_trades"] = [(f"{r.short}/{r.long}", str(r.entry)[:10], round(100 * r.net, 2)) for r in tr.nsmallest(5, "net").itertuples()]
    eq1, p1, d1 = equity(tr, 1)
    _, p2, d2 = equity(tr, 2)
    worst_usdt = float(LEG * tr.net.min())
    out["step2"] = {"profit_usdt": round(p1, 1), "profit_usdt_2x": round(p2, 1), "max_dd_pct": round(d1, 1),
                    "max_dd_pct_2x": round(d2, 1), "worst_trade_usdt": round(worst_usdt, 1),
                    "worst_trade_pct_of_account": round(100 * worst_usdt / 300, 1),
                    "pass": bool(p1 > 0 and p2 > 0 and d1 >= -35 and worst_usdt >= -30),
                    "by_year_usdt": {str(y): round(float(g.iloc[-1] - g.iloc[0]), 1) for y, g in eq1.groupby(eq1.index.year)}}
    eq1.resample("D").last().to_csv(b5.OUT / "x6_equity.csv")
    (b5.OUT / "x6_check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
