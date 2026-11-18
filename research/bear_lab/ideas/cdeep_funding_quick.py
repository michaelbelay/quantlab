"""cdeep_funding signal held 24h only (no target): the carry payers' selling is front-loaded.
Written 2026-11-09 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 24, 0.08, None, 72
REASON = "Longs paying funding in a coin's own bear cut on the next day's weakness; after ~a day 2024-26 dip buyers step in, so the short should not sit through the rebound."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480))
