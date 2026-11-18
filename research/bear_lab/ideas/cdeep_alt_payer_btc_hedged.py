"""Coin in its own deep bear still pays funding >= 0.01% while BTC's last funding is below 0.01% (shorts present in BTC).
Written 2026-11-09 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "When the market has already shorted BTC (funding under the default) but longs in a weak alt still pay full funding, those alt longs are the stale, unhedged book that sells next."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    btc_soft = P["FUND_LAST"]["BTC"] < 0.0001
    bs = pd.DataFrame({c: btc_soft for c in C.columns}, index=C.index)
    keep = pd.Series([c != "BTC" for c in C.columns], index=C.columns)
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480)) & bs & keep
