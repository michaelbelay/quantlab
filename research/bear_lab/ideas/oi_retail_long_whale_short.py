"""Retail accounts long-heavy (rank >= 0.80) while top traders lean short (rank <= 0.30), under the 480h EMA.
Written 2026-11-02 (main session, OI round 3)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "When the crowd and the big books disagree in a downtrend, the big books are the ones with information."
def signals(P):
    C = P["C"]
    return (bl.rank_prev(P["LS"]) >= 0.80) & (bl.rank_prev(P["TOP"]) <= 0.30) & (C < bl.ema(C, 480))
