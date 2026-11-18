"""Large cap in its own deep bear, under its falling 480h EMA, coin 20d volatility at or below its 1-year median; once a
day at 23:00, no funding condition. Written 2026-11-10 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "A calm large cap in its own bear has a wide holder base selling slowly and too little volatility to squeeze shorts; tests whether that alone bleeds without the funding signal."
MAJORS = ["BTC", "ETH", "BNB", "SOL", "XRP", "LINK", "ADA", "DOGE"]
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    e = bl.ema(C, 480)
    v = C.pct_change(fill_method=None).rolling(480, min_periods=480).std()
    calm = v <= v.rolling(8760, min_periods=4800).median()
    keep = pd.Series([c in MAJORS for c in C.columns], index=C.columns)
    at23 = pd.Series(C.index.hour == 23, index=C.index)
    sig = coin_deep(C) & (C < e) & (e < e.shift(24)) & calm & keep
    return sig.mul(at23, axis=0).astype(bool)
