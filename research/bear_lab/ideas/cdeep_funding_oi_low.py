"""cdeep_funding signal only while OI is in the lowest quarter of its last 30 days.
Leverage is flushed on both sides: no short fuel for a squeeze, longs still pay. Written 2026-11-05 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "With OI near a 30-day low there are few shorts left to cover, so the rallies that stop shorts out lack fuel while remaining longs keep paying and selling."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    low_oi = bl.rank_prev(P["OI"], 720) <= 0.25
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480)) & low_oi
