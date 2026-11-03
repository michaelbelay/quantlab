"""Hourly bar with top-1% volume of the month that closes in its bottom 25% after a +5% 24h run, under the 480h EMA.
Written 2026-11-02 (main session, round 4: timing and flow)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import numpy as np
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 24, 0.05, None, 24
REASON = "A volume spike that ends in a long upper wick is buyers exhausted and sellers absorbing at the top."
def signals(P):
    C, Hh, L, V = P["C"], P["H"], P["L"], P["QV"]
    pos = (C - L) / (Hh - L).replace(0, np.nan)
    return (bl.rank_prev(V) >= 0.99) & (pos <= 0.25) & (C / C.shift(24) - 1 >= 0.05) & (C < bl.ema(C, 480))
