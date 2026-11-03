"""Coin in its own deep bear lags BTC by >= 5 points over 7 days (checked at the 23:00 close). Short 168h.
Written 2026-11-02 (main session, round 5: the coin's own deep bear)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 168, 0.10, None, 168
REASON = "A coin in its own bear market that keeps losing to BTC is being sold by funds rotating out; rotation lasts weeks."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C, I = P["C"], P["INDEX"]
    r7 = C / C.shift(168) - 1
    rel = r7.sub(r7["BTC"], axis=0) <= -0.05
    d = pd.DataFrame({c: I.hour == 23 for c in C.columns}, index=I)
    m = coin_deep(C) & rel & d
    m["BTC"] = False
    return m
