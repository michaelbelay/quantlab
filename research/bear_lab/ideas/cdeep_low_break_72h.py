"""Coin in its own deep bear closes under its prior 72h low while longs still pay funding (last settled >= +0.01%).
Frequent cousin of cdeep_low_break_carry (30d) / _14d, built for the consistency rule. Written 2026-11-12 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "Longs still paying funding in a coin's own bear keep stops under the last 3-day low; each break fires them, and the breaks come at different hours for different coins, so entries spread over many days."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    low72 = C.rolling(72, min_periods=72).min().shift(1)
    return coin_deep(C) & (C < low72) & (P["FUND_LAST"] >= 0.0001)
