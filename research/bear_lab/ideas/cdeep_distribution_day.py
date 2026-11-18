"""Coin in its own deep bear falls >= 4% in 24h on >= 2x its usual 24h turnover while longs still pay funding.
Written 2026-11-10 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "A heavy-volume sell-off while funding stays positive is a large holder distributing into leveraged longs who have not been flushed yet; they are the next sellers."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    q24 = P["QV"].rolling(24, min_periods=24).sum()
    usual = q24.rolling(720, min_periods=720).median().shift(24)
    r24 = C / C.shift(24) - 1
    return coin_deep(C) & (q24 >= 2 * usual) & (r24 <= -0.04) & (P["FUND_LAST"] >= 0.0001)
