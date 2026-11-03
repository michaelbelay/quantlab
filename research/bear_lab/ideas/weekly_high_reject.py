"""Bar high reaches the prior 168h high but closes >= 3% below it, under a falling 480h EMA. Short 48h.
Written 2026-11-02 (main session, round 4: timing and flow)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import numpy as np
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 48, 0.06, None, 48
REASON = "Sellers who missed the last high defend it; a sharp rejection at the weekly high marks a lower high in a downtrend."
def signals(P):
    C, Hh = P["C"], P["H"]
    prev = Hh.shift(1).rolling(167, min_periods=167).max()
    e = bl.ema(C, 480)
    return (Hh >= prev) & (C <= 0.97 * Hh) & (C < e) & (e < e.shift(168))
