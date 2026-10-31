"""Is the live account signal-constrained or capital-constrained?

The distinction decides the whole question. If signals are scarce, loosening
filters buys trades. If the BOOK is the bottleneck, extra signals are simply
refused on arrival and every filter we relaxed cost expectancy for nothing.

So: replay the same signal stream through books of different sizes, and also
apply VBreak4Live's own same-direction cap, which refuses further.

    python research/slot_sensitivity.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "engine"))
from backtest import Config, simulate_pair   # noqa: E402
from features import load_pair               # noqa: E402
from frequency_baseline import LIVE_CFG, LIVE_SPEC, live_universe, load  # noqa: E402

MAX_SAME_DIRECTION = 10   # VBreak4Live


def replay(trades, slots, same_dir_cap=None):
    """Chronological replay. Returns (taken, refused_full, refused_direction)."""
    taken, full, samedir = [], 0, 0
    book = []          # (exit_ts, side)
    for t in sorted(trades, key=lambda x: x["entry"]):
        book = [b for b in book if b[0] > t["entry"]]
        if len(book) >= slots:
            full += 1
            continue
        if same_dir_cap is not None:
            if sum(1 for b in book if b[1] == t["side"]) >= same_dir_cap:
                samedir += 1
                continue
        taken.append(t)
        book.append((t["exit"], t["side"]))
    return taken, full, samedir


def main() -> int:
    uni, _ = load(live_universe())
    cfg = Config(**LIVE_CFG)
    rows = []
    for pair, f in uni.items():
        for t in simulate_pair(f, LIVE_SPEC, cfg, pair):
            rows.append({"pair": pair, "side": "long" if t.side > 0 else "short",
                         "pnl": t.pnl,
                         "entry": pd.Timestamp(f.date[t.entry_i]),
                         "exit": pd.Timestamp(f.date[t.exit_i])})
    df = pd.DataFrame(rows)
    df["entry"] = pd.to_datetime(df.entry, utc=True)
    df["exit"] = pd.to_datetime(df.exit, utc=True)
    yrs = (df.entry.max() - df.entry.min()).days / 365.25
    recs = df.to_dict("records")

    print(f"signal stream: {len(df):,} signals over {yrs:.2f} years "
          f"= {len(df)/yrs:,.0f} signals/year\n")
    print(f"{'slots':>6}{'taken/yr':>11}{'refused full':>14}{'refusal %':>11}"
          f"{'PF of taken':>13}{'marginal':>10}")
    prev = None
    out = {}
    for slots in (5, 10, 15, 20, 25, 30, 40, 60, 127):
        taken, full, _ = replay(recs, slots)
        t = pd.DataFrame(taken)
        w = t[t.pnl > 0].pnl.sum(); l = -t[t.pnl < 0].pnl.sum()
        per_yr = len(t) / yrs
        marg = "" if prev is None else f"{per_yr - prev:+.0f}"
        print(f"{slots:>6}{per_yr:>11,.0f}{full:>14,}{full/len(df)*100:>10.1f}%"
              f"{w/l:>13.3f}{marg:>10}")
        out[slots] = round(per_yr)
        prev = per_yr

    print()
    taken20, full20, sd20 = replay(recs, 20, MAX_SAME_DIRECTION)
    t20 = pd.DataFrame(taken20)
    print(f"WITH VBreak4Live's same-direction cap ({MAX_SAME_DIRECTION} of 20):")
    print(f"  taken {len(t20):,} = {len(t20)/yrs:,.0f}/yr ({len(t20)/yrs/52:.1f}/week)")
    print(f"  refused: {full20:,} full book, {sd20:,} same-direction "
          f"({(full20+sd20)/len(df)*100:.1f}% total)")
    w = t20[t20.pnl > 0].pnl.sum(); l = -t20[t20.pnl < 0].pnl.sum()
    print(f"  profit factor {w/l:.3f}  expectancy {t20.pnl.mean():+.3f} USDT/trade")
    print(f"\n  NOTE: the correlation cap (max 4 above 0.80) refuses further still and is")
    print(f"  not modelled here, so the live figure is a little BELOW this line.")

    (ROOT / "research" / "results" / "slot_sensitivity.json").write_text(
        json.dumps({"signals_per_year": round(len(df) / yrs), "by_slots": out,
                    "live_gates_per_year": round(len(t20) / yrs)}, indent=2) + "\n",
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
