"""Coin in its own deep bear: top-trader long/short position ratio down >= 10% in 72h while longs still pay funding >= +0.01%.
Written 2026-11-08 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Big accounts cutting longs while the rest still pay funding means informed money is leaving and the remaining longs are the next sellers."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    top_chg = P["TOP"] / P["TOP"].shift(72) - 1
    return coin_deep(C) & (top_chg <= -0.10) & (P["FUND_LAST"] >= 0.0001)
