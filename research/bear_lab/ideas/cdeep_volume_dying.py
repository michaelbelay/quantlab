"""Coin in its own deep bear, under its 480h EMA, with 7-day traded volume in the lowest 10% of its last 180 days.
Interest has left the coin. No funding condition. Written 2026-11-06 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "When traders leave a coin in its own bear, the steady sellers (unlocks, treasuries, miners) meet no bid and push it lower; there is little short interest left to squeeze."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    q7 = P["QV"].rolling(168, min_periods=168).sum()
    dying = q7 <= q7.rolling(4320, min_periods=2160).quantile(0.10)
    return coin_deep(C) & (C < bl.ema(C, 480)) & dying
