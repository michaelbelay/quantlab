"""One hour before a funding settlement with last funding >= +0.03%: short for 4h, collect funding.
Written 2026-11-02 (main session, round 4: timing and flow)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import numpy as np
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 4, 0.03, None, 8
REASON = "Longs facing a high funding bill close before settlement; the short also receives the payment."
def signals(P):
    C, I = P["C"], P["INDEX"]
    pre = pd.DataFrame({c: np.isin(I.hour, [6, 14, 22]) for c in C.columns}, index=I)   # closes 1h before 08/16/00
    return pre & (P["FUND_LAST"] >= 0.0003)
