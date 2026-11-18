"""Coin in its own deep bear fell >= 10% in 72h, yet funding still settles >= +0.01%.
Dip buyers re-levered long into the drop. Written 2026-11-04 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "After a 10% drop in a coin's own bear, full positive funding means leveraged dip buyers, not shorts; the next leg liquidates them."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C, F = P["C"], P["FUND"]
    return coin_deep(C) & (C / C.shift(72) - 1 <= -0.10) & (F >= 0.0001)
