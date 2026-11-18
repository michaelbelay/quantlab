"""cdeep_funding only while at most 10% of the 19 coins have negative last funding (no short crowding anywhere).
Written 2026-11-10 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Squeezes need crowded shorts; when almost no coin has negative funding there is no squeeze fuel market-wide, so a carry short in a coin's own bear just bleeds."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    calm_shorts = share_neg <= 0.10
    base = coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480))
    return base.mul(calm_shorts, axis=0).astype(bool)
