"""Coin in its own deep bear and at least 50% below its 200-day high, longs not paid (funding >= 0) at settlement.
Broken coins: every holder is underwater. Written 2026-11-04 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "A coin down half from its 200-day high has only underwater holders; they sell any strength to get out, and no short crowd fuels squeezes."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C, F = P["C"], P["FUND"]
    hi = C.rolling(4800, min_periods=4800).max()
    return coin_deep(C) & (C <= 0.5 * hi) & (F >= 0) & (C < bl.ema(C, 480))
