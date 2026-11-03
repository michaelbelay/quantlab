"""Coin in its own deep bear: the bar's high touches the 480h EMA and it closes >= 2% under it.
Written 2026-11-02 (main session, round 6: positioning inside the coin's own deep bear)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import numpy as np
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Holders under water since the EMA level sell at break-even; the falling average caps the bounce."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    return coin_deep(C) & ((P["H"] >= bl.ema(C, 480)) & (C <= 0.98 * bl.ema(C, 480)))
