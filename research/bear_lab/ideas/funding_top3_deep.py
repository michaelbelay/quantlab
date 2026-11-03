"""Deep bear: at its funding settlement a coin is among the 3 highest funding rates of the 19 (and > 0), under its 480h EMA.
Short the most crowded long relative to the rest. Written 2026-11-02 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "In a deep bear the coin whose longs pay the most relative to the market is the most crowded long book; it is first in line when margin calls cascade, and the short is paid to wait."
def signals(P):
    C, F, FL = P["C"], P["FUND"], P["FUND_LAST"]
    r = FL.where(P["ELIG"]).rank(axis=1, ascending=False)
    deep = pd.DataFrame({c: P["DEEP"] for c in C.columns})
    return deep & F.notna() & (r <= 3) & (FL > 0) & (C < bl.ema(C, 480))
