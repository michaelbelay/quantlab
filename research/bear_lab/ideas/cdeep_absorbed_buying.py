"""Coin in its own deep bear: 24h taker buy/sell at a 30-day high but the 24h return <= 0.
Written 2026-11-02 (main session, round 6: positioning inside the coin's own deep bear)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import numpy as np
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 48, 0.07, None, 48
REASON = "Market buying absorbed without a rise in a coin's own bear market means a large holder is exiting into it."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    return coin_deep(C) & ((bl.rank_prev(P["TAKER"].rolling(24, min_periods=24).mean()) >= 0.90) & (C / C.shift(24) - 1 <= 0))
