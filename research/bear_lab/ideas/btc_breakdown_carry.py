"""Coin in its own deep bear, longs paying funding >= 0.01%, under its 480h EMA, and BTC made a new 30-day closing low
in the last 24h. Written 2026-11-06 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "A BTC break to a new 30-day low sets off liquidations; alts whose longs are still paying funding in their own bear are the ones that get flushed."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    btc = C["BTC"]
    new_low = btc <= btc.shift(1).rolling(720, min_periods=720).min()
    recent = new_low.astype(float).rolling(24, min_periods=1).max() > 0
    R = pd.DataFrame({c: recent for c in C.columns}, index=C.index)
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480)) & R
