"""Coin in its own deep bear: funding > 0 at every settlement of the last 3 days (9 in a row), checked at a settlement.
Written 2026-11-02 (main session, round 6: positioning inside the coin's own deep bear)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import numpy as np
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Longs who keep paying for 3 days in a coin's own bear market are stubborn holders who capitulate together."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    return coin_deep(C) & ((P["FUND"] > 0) & ((P["FUND"].ffill() > 0).rolling(65, min_periods=65).min() > 0) & (C < bl.ema(C, 480)))
