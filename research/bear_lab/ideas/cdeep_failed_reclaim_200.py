"""Coin closed above its falling 200-day average in the last 7 days and is now back under it and under its 168h EMA,
with funding not negative. Written 2026-11-08 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Traders who bought the 'bear is over' reclaim of the 200-day average with leverage are trapped when it fails, and their stops sit just under the level."
def signals(P):
    C = P["C"]
    s = C.rolling(4800, min_periods=4800).mean()
    falling = s < s.shift(480)
    was_above = (C > s).astype(float).rolling(168, min_periods=168).max() > 0
    return falling & (C < s) & was_above & (C < bl.ema(C, 168)) & (P["FUND_LAST"] >= 0)
