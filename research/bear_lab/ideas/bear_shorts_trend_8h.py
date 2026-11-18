"""Any bear day: at each of the coin's funding settlements (the bar where its funding settles), the coin is under its
480h EMA and at most 10% of the 19 coins have negative last funding. No own-funding condition. Same regime as
bear_calm_shorts_trend (23:00 daily, 13% of bear days) but checked at every settlement with a 24h gap, written for
frequency. Written 2026-11-14 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "No short crowd anywhere means no squeeze fuel, so a coin under its trend bleeds in a shallow bear whatever its own funding rate; checking at every settlement instead of once a day catches each day the regime holds."
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    calm_shorts = share_neg <= 0.10
    base = P["FUND"].notna() & (C < bl.ema(C, 480))
    return base.mul(calm_shorts, axis=0).astype(bool)
