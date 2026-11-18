"""Coin in its own deep bear closes under its prior 30-day low while longs still pay funding (last settled >= +0.01%).
Written 2026-11-07 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Longs still paying to hold a coin in its own bear keep their stops under the obvious 30-day low; the break triggers those stops and liquidations, so sellers are forced."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    low30 = C.rolling(720, min_periods=720).min().shift(1)
    return coin_deep(C) & (C < low30) & (P["FUND_LAST"] >= 0.0001)
