"""Coin in its own deep bear and among the 3 highest funding rates of the 19 at a settlement (> 0), under its 480h EMA.
Written 2026-11-02 (main session, round 5: the coin's own deep bear)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Within coins in their own bear market, the most crowded long book pays the most and unwinds first."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C, F = P["C"], P["FUND"]
    top = F.rank(axis=1, ascending=False, method="first") <= 3
    return coin_deep(C) & top & (F > 0) & (C < bl.ema(C, 480))
