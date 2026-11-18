"""Coin in its own deep bear, funding >= 0.01% at settlement, 30-day return >= 10 pts worse than BTC's, under its 480h EMA.
Written 2026-11-03 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "A coin falling behind BTC for its own reasons while its longs still pay has no market tide to rescue it; the holders are betting on a turn that the flows do not support."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    r = C / C.shift(720) - 1
    rel = r.sub(r["BTC"], axis=0)
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (rel <= -0.10) & (C < bl.ema(C, 480))
