"""Coin in its own deep bear closes under its prior 24h low while longs still pay funding (last settled >= +0.01%).
Most frequent version of the low-break-in-carry idea. Written 2026-11-12 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "Day traders long a coin in its own bear while paying funding sit with stops under yesterday's low; a close under it fires them nearly every bear day on some coin."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    low24 = C.rolling(24, min_periods=24).min().shift(1)
    return coin_deep(C) & (C < low24) & (P["FUND_LAST"] >= 0.0001)
