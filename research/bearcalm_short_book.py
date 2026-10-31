"""VBreak4 SHORTS in Bear-Calm as the real 300 USDT account - descriptive backtest, 2026-10-12 (Michael: "go run the bear backtest").

    C:\\quantlab\\.venv\\Scripts\\python.exe research\\bearcalm_short_book.py      (cwd = C:\\quantlab)

Same trades, coin filter (point-in-time top 133 by volume), BTC condition and book replay as vbreak_conditions.py,
cut to what the paper bot C:\\quantlab\\bots\\strategies\\VBreak4BearCalmShort.py does: shorts only, entries only while BTC
is Bear-Calm. 20 slots, <= 10 shorts, stake = equity / 20, mainnet minimum orders, 1x.
The short side was picked AFTER the 2026-10-11 conditions result showed it, so this describes, it does not prove.
The verdict stays with the forward test (C:\\quantlab\\FORWARD_2026-10-11_bearcalm_short.md).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vbreak_conditions import ROOT, TOP, YEARS, book, load_trades, min_notional, tag, trade_stats  # noqa: E402

OUT = ROOT / "research" / "BEARCALM_SHORT_BOOK_2026-10-12"


def best_week_share(t: pd.DataFrame) -> float | None:
    w = t.groupby(t["exit_date"].dt.to_period("W"))["pnl"].sum()
    return round(float(w.max() / w.sum()), 3) if w.sum() > 0 else None


def main() -> None:
    t = tag(load_trades())
    t = t[t["cond_ok"] & (t["liq_rank"] <= TOP) & (t["cell"] == "Bear-Calm") & (t["side"] == "short")].copy()
    mn = min_notional()
    x2 = t.assign(pnl=t["pnl"] - 0.20)                 # costs doubled (+0.20 per 100 notional per trade)
    top3 = t.drop(t["pnl"].nlargest(3).index)
    out = {"trades": trade_stats(t), "book": book(t, mn), "book_costs_x2": book(x2, mn),
           "book_without_best_3_trades": book(top3, mn), "best_week_share_of_profit": best_week_share(t)}
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
