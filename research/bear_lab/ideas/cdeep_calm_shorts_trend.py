"""Coin in its own deep bear and under its EMA480 while <= 10% of the 19 coins have negative funding; no own-funding
condition, once a day. Tests whether market-wide absence of shorts alone carries the edge. Written 2026-11-11 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Squeezes need crowded shorts; with almost no coin paying negative funding there is no squeeze fuel, so a coin in its own bear keeps bleeding."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    calm_shorts = (share_neg <= 0.10) & pd.Series(P["INDEX"].hour == 23, index=P["INDEX"])
    base = coin_deep(C) & (C < bl.ema(C, 480))
    return base.mul(calm_shorts, axis=0).astype(bool)
