"""Coin in its own deep bear closes at a new 30-day low while OI rose >= 3% in 24h. Short 72h.
Written 2026-11-02 (main session, round 5: the coin's own deep bear)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "New lows on rising OI in a coin's own bear market are fresh shorts plus trapped longs: the stops below fuel the move."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C, OI = P["C"], P["OI"]
    low = C.shift(1).rolling(719, min_periods=719).min()
    return coin_deep(C) & (C < low) & (OI / OI.shift(24) - 1 >= 0.03)
