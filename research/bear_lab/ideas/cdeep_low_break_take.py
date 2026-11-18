"""cdeep_low_break_carry entries (close under the prior 30-day low, own deep bear, longs paying) with a 5% take-profit.
Written 2026-11-10 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, 0.05, 72
REASON = "Stop runs under an obvious low flush fast, and in 2024-26 dip buyers reverse them within days; take the 5% cascade instead of holding into the rebound."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    low30 = C.rolling(720, min_periods=720).min().shift(1)
    return coin_deep(C) & (C < low30) & (P["FUND_LAST"] >= 0.0001)
