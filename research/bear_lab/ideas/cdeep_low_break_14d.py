"""Coin in its own deep bear closes under its prior 14-day low while longs still pay funding (last settled >= +0.01%).
Written 2026-11-08 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Leveraged longs who still pay funding in a coin's own bear park their stops under the recent 2-week swing low; breaking it fires those stops and liquidations."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    low14 = C.rolling(336, min_periods=336).min().shift(1)
    return coin_deep(C) & (C < low14) & (P["FUND_LAST"] >= 0.0001)
