"""13:00 UTC (before the US open), coin under its 480h EMA and down over 24h: short for 8h.
Written 2026-11-02 (main session, round 4: timing and flow)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import numpy as np
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 8, 0.04, None, 20
REASON = "In bear phases US hours carry the selling (ETF and fund de-risking); weak coins get sold first."
def signals(P):
    C, I = P["C"], P["INDEX"]
    t = pd.DataFrame({c: I.hour == 12 for c in C.columns}, index=I)   # bar 12:00 closes at 13:00
    return t & (C / C.shift(24) - 1 < 0) & (C < bl.ema(C, 480))
