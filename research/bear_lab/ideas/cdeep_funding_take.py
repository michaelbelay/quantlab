"""cdeep_funding signal with a 5% take-profit: bank the flush instead of holding into the rebound.
Written 2026-11-07 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, 0.05, 72
REASON = "In 2024-26 dip buyers reverse flushes within days, so a carry short in a coin's own bear should take the 5% flush when it comes rather than give it back."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480))
