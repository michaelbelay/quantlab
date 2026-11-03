"""Coin in its own deep bear rallies >= 8% in 72h but stays under its 480h EMA. Short 72h.
Written 2026-11-02 (main session, round 5: the coin's own deep bear)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "In a coin's own bear market every holder under water sells a rally; BTC's regime does not change that supply."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    return coin_deep(C) & (C / C.shift(72) - 1 >= 0.08) & (C < bl.ema(C, 480))
