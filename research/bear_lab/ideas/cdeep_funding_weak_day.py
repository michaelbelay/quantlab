"""cdeep_funding signal only when the coin is down over the last 24h and closes in the lower half of its 24h range.
Enter while the carry payers are under pressure, not on a bounce. Written 2026-11-06 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Longs paying funding on a down day in a coin's own bear are already under water and sell into the next sessions; shorting their bounce lost (cdeep_funding_bounce)."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    hi = P["H"].rolling(24, min_periods=24).max()
    lo = P["L"].rolling(24, min_periods=24).min()
    weak = (C / C.shift(24) - 1 < 0) & (C <= (hi + lo) / 2)
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480)) & weak
