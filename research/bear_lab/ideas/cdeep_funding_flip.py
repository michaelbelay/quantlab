"""Coin in its own deep bear: funding settles >= +0.01% after a settlement <= 0 within the last 24h. Short 72h.
Written 2026-11-02 (main session, round 5: the coin's own deep bear)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Longs re-entering a coin in its own bear market (funding flips positive) are early bottom pickers who get stopped out."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C, F = P["C"], P["FUND"]
    neg = (F <= 0).astype(float).shift(1).rolling(24, min_periods=1).max() > 0
    return coin_deep(C) & (F >= 0.0001) & neg & (C < bl.ema(C, 480))
