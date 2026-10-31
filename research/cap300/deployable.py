"""MAJORS-TREND, deployable form: orders only on decision days, every weekday anchor, out-of-time and full span.

Added 2026-10-04 after the bot build showed (a) the research simulator re-targeted size daily while the bot
acts weekly, and (b) the weekly result moved a lot with the rebalance weekday. The rule itself is unchanged
(20-day return > 0, 40% vol target, cap 2 per coin, one third each, 1x gross cap); only the execution schedule
is now the one a bot follows. Reported for every anchor; nothing is selected by these numbers except the
schedule decision stated in the output (daily vs weekly), which is judged on 2017-2020 only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[0] / "pipeline")]
import out_of_time as O  # noqa: E402
import run_round as RR  # noqa: E402
import sim as SM  # noqa: E402

COINS = ["BTC", "ETH", "BNB"]


def panel():
    L = RR.panels()["live"]
    old = O.panel(COINS)
    D = {k: pd.concat([old[k].loc[:"2020-12-31"], L[k].reindex(columns=COINS).loc["2021-01-01":]]).sort_index()
         for k in ("close", "high", "low", "qvol", "funding")}
    D["ret"] = D["close"].pct_change(fill_method=None)
    return D


def weights(D):
    c = D["close"][COINS]
    ret = c / c.shift(20) - 1
    vol = D["ret"][COINS].rolling(30, min_periods=20).std() * np.sqrt(365)
    w = ((0.40 / vol).clip(upper=2.0) / 3).where(ret > 0, 0.0).fillna(0.0)
    return w.div(np.maximum(w.sum(axis=1), 1.0), axis=0)


def run(D, w, mask, start, end, minn):
    W = w.where(mask, np.nan).ffill().fillna(0.0).loc[start:end]
    sub = {k: v.loc[start:end] for k, v in D.items()}
    r = SM.simulate(W, sub, minn=minn, trade_days=mask.loc[start:end])
    m = SM.metrics(r)
    m2 = SM.metrics(SM.simulate(W, sub, minn=minn, trade_days=mask.loc[start:end], cost_mult=2.0))
    return m, m2


def main():
    D = panel()
    minn = SM.min_notionals()
    w = weights(D)
    idx = w.index
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    print("decision day = the day whose close is used; orders at the next open")
    for label, start, end in (("OUT-OF-TIME 2017-08 -> 2020-12", "2017-08-17", "2020-12-31"), ("FULL 2017-08 -> 2026-09", "2017-08-17", "2026-09-21"),
                              ("2021-01 -> 2026-09", "2021-01-01", "2026-09-21")):
        print(f"\n{label}")
        rows = []
        for wd in range(7):
            mask = pd.Series(idx.weekday == wd, index=idx)
            m, m2 = run(D, w, mask, start, end, minn)
            rows.append((names[wd], m, m2))
            print(f"  weekly {names[wd]}: 300 -> {m['final']:7.0f} (2x {m2['final']:7.0f}) CAGR {m['cagr']:+.1%} DD {m['max_dd']:.0%} trades {m['trades']}")
        f = [r[1]["final"] for r in rows]
        print(f"  weekly, all 7 anchors: median {np.median(f):.0f}, min {min(f):.0f}, max {max(f):.0f}; DD median {np.median([r[1]['max_dd'] for r in rows]):.0%}, worst {max(r[1]['max_dd'] for r in rows):.0%}")
        m, m2 = run(D, w, pd.Series(True, index=idx), start, end, minn)
        print(f"  daily (no anchor): 300 -> {m['final']:7.0f} (2x {m2['final']:7.0f}) CAGR {m['cagr']:+.1%} DD {m['max_dd']:.0%} trades {m['trades']} orders {m['executed_orders']}")


if __name__ == "__main__":
    main()
