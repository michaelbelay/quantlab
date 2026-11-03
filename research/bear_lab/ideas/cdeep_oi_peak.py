"""Coin in its own deep bear while OI USDT is at a 30-day high (rank >= 0.95) and price under its 480h EMA.
Written 2026-11-02 (main session, round 6: positioning inside the coin's own deep bear)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import numpy as np
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Peak leverage in a coin that is in its own bear market is mostly underwater longs: liquidation fuel."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    return coin_deep(C) & ((bl.rank_prev(P["OI"]) >= 0.95) & (C < bl.ema(C, 480)))
