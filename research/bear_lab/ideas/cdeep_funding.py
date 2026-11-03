"""Coin in its own deep bear (under a falling 200-day average) with funding >= +0.01% at settlement, under its 480h EMA.
Written 2026-11-02 (main session, round 5: the coin's own deep bear)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "The carry edge needs a coin in a real bear market, not BTC's: longs paying to hold a coin in its own deep bear bleed out."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480))
