"""Any bear day: at a funding settlement the coin pays >= +0.01% and so did every settlement of the last 24h (at least
three paying settlements, none below the default rate), the coin is under its 480h EMA, and at most 10% of the 19 coins
have negative last funding. Shallow-bear version of the persistence idea (cdeep_funding_persist, 9 settlements) with a
one-day window so it still fires often. Written 2026-11-15 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "Longs that have paid the full rate for a whole day under their trend had no relief bar to exit into; the longer the bill runs with no short crowd to squeeze for them, the more of them give up together."
def signals(P):
    C, F, FL = P["C"], P["FUND"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    calm_shorts = share_neg <= 0.10
    paid = (F >= 0.0001).astype(float).rolling(24, min_periods=24).sum() >= 3
    none_below = (F < 0.0001).astype(float).rolling(24, min_periods=24).sum() == 0
    base = (F >= 0.0001) & paid & none_below & (C < bl.ema(C, 480))
    return base.mul(calm_shorts, axis=0).astype(bool)
