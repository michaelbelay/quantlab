"""Coin in its own deep bear falls >= 5% in 7 days while the all-account long/short ratio rises >= 10% (retail adds longs).
Written 2026-11-07 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Retail accounts averaging down into a falling coin are the next forced sellers when their margin runs out; the change (not the level) shows new trapped longs."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C, LS = P["C"], P["LS"]
    ls_up = (LS / LS.shift(168) - 1) >= 0.10
    down = (C / C.shift(168) - 1) <= -0.05
    return coin_deep(C) & ls_up & down
