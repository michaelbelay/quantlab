"""Top traders hold their most long-heavy book of the month while the coin sits under a falling 480h EMA.
Written 2026-11-02 (main session, OI round 3)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Big accounts loaded long into a downtrend are the next forced sellers; O4 showed the opposite crowd (top short) loses."
def signals(P):
    C = P["C"]
    e = bl.ema(C, 480)
    return (bl.rank_prev(P["TOP"]) >= 0.90) & (C < e) & (e < e.shift(168))
