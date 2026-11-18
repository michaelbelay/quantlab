"""cdeep_funding signal only while the coin's own 20-day hourly volatility is at or below its 1-year median.
Squeeze risk is coin-specific, so use the coin's calm, not BTC's. Written 2026-11-05 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "A coin bleeding quietly in its own bear while longs pay funding has no squeeze traders in it; volatile coins attract squeeze hunters who stop shorts out."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    v = C.pct_change(fill_method=None).rolling(480, min_periods=480).std()
    calm = v <= v.rolling(8760, min_periods=4800).median()
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480)) & calm
