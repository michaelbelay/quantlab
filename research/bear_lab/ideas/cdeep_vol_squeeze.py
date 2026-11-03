"""Coin in its own deep bear: 7-day realized volatility at a 30-day low (rank <= 0.10) under its 480h EMA.
Written 2026-11-02 (main session, round 6: positioning inside the coin's own deep bear)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import numpy as np
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 96, 0.08, None, 96
REASON = "Volatility compression in a coin's own bear market resolves in the trend direction as stops below are taken."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    return coin_deep(C) & ((bl.rank_prev((C / C.shift(1)).apply(np.log).rolling(168, min_periods=168).std()) <= 0.10) & (C < bl.ema(C, 480)))
