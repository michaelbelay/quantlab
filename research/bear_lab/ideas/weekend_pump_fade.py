"""Sunday 23:00 UTC close: coin up >= 4% over the weekend (48h) while under its 480h EMA. Short for 48h.
Written 2026-11-02 (main session, round 4: timing and flow)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import numpy as np
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 48, 0.06, None, 48
REASON = "Weekend rallies happen on thin books without institutional flow; Monday's real liquidity sells into them."
def signals(P):
    C, I = P["C"], P["INDEX"]
    sun = pd.DataFrame({c: (I.dayofweek == 6) & (I.hour == 23) for c in C.columns}, index=I)
    return sun & (C / C.shift(48) - 1 >= 0.04) & (C < bl.ema(C, 480))
