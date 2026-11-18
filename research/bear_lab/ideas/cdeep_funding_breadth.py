"""cdeep_funding signal only while at least 60% of the coins with a 200-day history are in their own deep bear.
A sector-wide bear, not a single weak coin. Written 2026-11-06 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "When most coins are in their own bear, crypto money is leaving the sector, so there is no rotation bid to squeeze a short in a coin whose longs still pay funding."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    cd = coin_deep(C)
    valid = C.rolling(4800, min_periods=4800).mean().notna()
    share = cd.sum(axis=1) / valid.sum(axis=1).where(lambda x: x > 0)
    B = pd.DataFrame({c: share >= 0.6 for c in C.columns}, index=C.index)
    return cd & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480)) & B
