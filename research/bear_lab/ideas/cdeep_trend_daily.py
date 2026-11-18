"""Coin in its own deep bear, under a falling 480h EMA, checked once a day at the daily close (no funding condition).
Baseline: does the coin's own long-term downtrend alone carry the short? Written 2026-11-04 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Holders of a coin under its falling 200-day average are underwater and trend funds stay short; supply keeps meeting no bid."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    e = bl.ema(C, 480)
    daily = pd.DataFrame({c: C.index.hour == 23 for c in C.columns}, index=C.index)
    return coin_deep(C) & (C < e) & (e < e.shift(168)) & daily
