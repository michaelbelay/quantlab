"""cdeep_funding signal only in the first days of a BTC bear spell (<= 72 of the last 168 hours were bear hours).
Written 2026-11-08 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "When BTC has just turned bear, longs in an already-weak coin are still positioned for the last up-move and must de-lever; later in a long bear spell they are already gone."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    b = P["BEAR"].astype(float).rolling(168, min_periods=168).sum() <= 72
    young = pd.DataFrame({c: b for c in C.columns}, index=C.index)
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480)) & young
