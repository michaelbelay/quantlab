"""Deep bear, funding >= +0.01% at settlement and OI up >= 10% in 7 days, under a falling 480h EMA.
Written 2026-11-02 (main session, OI round 3)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Longs adding size and paying carry in a deep bear are the fuel for the next liquidation leg."
def signals(P):
    C, F, OI = P["C"], P["FUND"], P["OI"]
    e = bl.ema(C, 480)
    deep = pd.DataFrame({c: P["DEEP"] for c in C.columns})
    return deep & (F >= 0.0001) & (OI / OI.shift(168) - 1 >= 0.10) & (C < e) & (e < e.shift(168))
