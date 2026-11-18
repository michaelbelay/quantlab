"""Any bear day: at a funding settlement the coin pays >= +0.01%, is under its 480h EMA, and the market has had at most
10% of the 19 coins with negative last funding for every hour of the last 24h (the no-shorts state has held through the
last three settlements, not only the current one). Tests whether the sharp 10% threshold is more robust when the state
persists. Written 2026-11-15 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "A short crowd that has been absent for a full day has not merely been flushed by one wick; it is not there, so the longs paying funding under their trend face a day without squeeze fuel."
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    calm_hours = (share_neg <= 0.10).astype(float).rolling(24, min_periods=24).sum()
    calm_held = calm_hours >= 24
    base = (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480))
    return base.mul(calm_held, axis=0).astype(bool)
