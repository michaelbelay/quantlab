"""Coin in its own deep bear: open interest / 24h volume in the top 10% of its last 30 days while longs pay funding >= +0.01%.
Written 2026-11-08 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Much open leverage and little turnover in a falling coin means stale long positions that are paying to hold; they cannot exit quietly when the next leg down starts."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    lev = P["OI"] / P["QV"].rolling(24, min_periods=24).sum()
    return coin_deep(C) & (bl.rank_prev(lev, 720) >= 0.90) & (P["FUND_LAST"] >= 0.0001)
