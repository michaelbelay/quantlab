"""Coin in its own deep bear, down >= 20% over 30 days, and longs still pay funding >= +0.01% at the settlement.
Written 2026-11-08 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Longs who keep paying funding after a 20% monthly loss are in denial with leverage; nobody is short enough to squeeze, so the next drop forces them out."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    return coin_deep(C) & (C / C.shift(720) - 1 <= -0.20) & (P["FUND"] >= 0.0001)
