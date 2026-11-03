"""Coin in its own deep bear while all-account long/short ratio is at a 30-day high (rank >= 0.90).
Written 2026-11-02 (main session, round 6: positioning inside the coin's own deep bear)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import numpy as np
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Retail buying the dip of a coin in its own bear market is the supply that sells on the next leg down."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    return coin_deep(C) & (bl.rank_prev(P["LS"]) >= 0.90)
