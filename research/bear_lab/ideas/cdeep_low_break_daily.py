"""Coin in its own deep bear: the daily close (23:00 bar) is under the lowest of the prior 30 daily closes while longs
still pay funding (last settled >= +0.01%). Written 2026-11-10 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Swing longs and funds act on daily closes; a daily close under the 30-day closing low makes them cut, and longs still paying funding are the ones left to sell."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    dc = C[C.index.hour == 23]
    brk = (dc < dc.rolling(30, min_periods=30).min().shift(1)).reindex(C.index).fillna(False).astype(bool)
    return coin_deep(C) & brk & (P["FUND_LAST"] >= 0.0001)
