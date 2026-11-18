"""Coin in its own deep bear, funding >= 0.01% at settlement, close < 168h EMA < 480h EMA (short and long trend down).
Written 2026-11-03 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "When the weekly trend is also down, the longs still paying carry are losing right now, not just on paper; their stops and margin calls sit below and get hit in sequence."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    e1, e2 = bl.ema(C, 168), bl.ema(C, 480)
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < e1) & (e1 < e2)
