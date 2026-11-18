"""cdeep_funding signal when the coin's last 7-day high is under the 7-day high before it (a lower weekly high).
Written 2026-11-09 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "A lower weekly high means last week's bounce buyers were sold into earlier; longs still paying funding on top of them are the next sellers, and no squeeze has reclaimed the prior high."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    hi = P["H"].rolling(168, min_periods=168).max()
    lower = hi < hi.shift(168)
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480)) & lower
