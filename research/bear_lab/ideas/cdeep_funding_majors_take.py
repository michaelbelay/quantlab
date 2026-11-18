"""cdeep_funding on the 8 large caps only, with a 5% take-profit.
Combines the two changes that lifted half B most (majors, take-profit). Written 2026-11-09 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, 0.05, 72
REASON = "Large-cap holders in their own bear sell slowly while longs pay funding, but 2024-26 dip buyers reverse flushes within days, so take the 5% when it comes."
MAJORS = ["BTC", "ETH", "BNB", "SOL", "XRP", "LINK", "ADA", "DOGE"]
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    sig = coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480))
    keep = pd.Series([c in MAJORS for c in C.columns], index=C.columns)
    return sig & keep
