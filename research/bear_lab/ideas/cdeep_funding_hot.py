"""Coin in its own deep bear with funding ABOVE the 0.01% floor (>= 0.015%) at settlement, under its 480h EMA.
A real perp premium, not the default rate. Written 2026-11-03 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Funding above the 0.01% floor means leveraged longs bid the perp over spot in a coin's own bear market; arbitrage shorts close that premium and the longs pay until they quit."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    return coin_deep(C) & (P["FUND"] >= 0.00015) & (C < bl.ema(C, 480))
