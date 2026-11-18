"""BTC deep bear (under its falling 200-day average): coin under its 480h EMA closes under its prior 72h low while its
longs still pay funding (last settled >= +0.01%). Uses BTC's deep bear instead of the coin's own, so it can fire on more
bear days. Written 2026-11-12 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "In a BTC deep bear there is no market bid to rescue a coin; longs still paying funding have stops under the 3-day low, and the break fires them coin by coin, hour by hour."
def signals(P):
    C = P["C"]
    deep = pd.DataFrame({c: P["DEEP"] for c in C.columns})
    low72 = C.rolling(72, min_periods=72).min().shift(1)
    return deep & (C < bl.ema(C, 480)) & (C < low72) & (P["FUND_LAST"] >= 0.0001)
