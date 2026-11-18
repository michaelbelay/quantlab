"""Coin in its own deep bear, funding >= 0.01% at settlement, up >= 3% in 24h, still under its 480h EMA.
Short the carry payers' first bounce. Written 2026-11-03 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Longs paying carry in a coin's own bear market are waiting to get out; a 24h bounce is their exit, so the bounce is sold and the short is paid funding while it fades."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C / C.shift(24) - 1 >= 0.03) & (C < bl.ema(C, 480))
