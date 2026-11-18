"""Alt whose coin/BTC ratio is under its falling 200-day average, funding >= +0.01% at settlement, coin under its 480h EMA.
The carry signal, but the bear is measured against BTC, not in USD. Written 2026-11-07 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "An alt in a long bear against BTC has no rotation buyer in the 2024-26 BTC-only bid; longs still paying funding on it are bag-holders who bleed out."
def signals(P):
    C = P["C"]
    R = C.div(C["BTC"], axis=0)
    s = R.rolling(4800, min_periods=4800).mean()
    m = (R < s) & (s < s.shift(480)) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480))
    m["BTC"] = False
    return m
