"""cdeep_funding signal while the coin's 24h quote volume is under its 30-day median of 24h volume.
Written 2026-11-09 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Longs paying to hold a coin in its own bear while turnover dries up have no new buyers to sell to; squeeze traders also stay away from quiet books."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    v24 = P["QV"].rolling(24, min_periods=24).sum()
    quiet = v24 < v24.rolling(720, min_periods=720).median()
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480)) & quiet
