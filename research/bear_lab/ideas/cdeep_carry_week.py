"""Coin in its own deep bear, funding >= 0.01% at settlement, under its 480h EMA; hold a week (168h, 12% stop).
Written 2026-11-03 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 168, 0.12, None, 168
REASON = "A carry short earns from slow bleeding, not a quick drop: longs holding a coin in its own bear sell over days as funding and losses add up, so a week-long hold with a wider stop collects more of it."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480))
