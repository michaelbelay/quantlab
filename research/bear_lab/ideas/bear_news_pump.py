"""Coin in its own deep bear: one 1h candle up >= 4% on >= 5x its 30-day median hourly volume (a news pump).
Written 2026-11-07 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 48, 0.10, None, 48
REASON = "In a coin's own bear most holders are underwater; a sudden news pump is the exit liquidity they wait for, so the spike is sold within days."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C, O, QV = P["C"], P["O"], P["QV"]
    med = QV.rolling(720, min_periods=720).median().shift(1)
    spike = (QV >= 5 * med) & (C / O - 1 >= 0.04)
    return coin_deep(C) & spike
