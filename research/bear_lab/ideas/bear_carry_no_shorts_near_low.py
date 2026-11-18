"""Any bear day: at a funding settlement the coin pays >= +0.01%, is under its 480h EMA, its close is within 5% of its
lowest close of the last 30 days (720h), and at most 10% of the 19 coins have negative last funding. A state (near the
lows) rather than an event (the break), so it fires on more days than the low-break ideas. Written 2026-11-15 by the
daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "Near the monthly low every long of the last month is under water and their stops sit just below; longs still paying funding there are the most exposed book in the market, and with no short crowd to squeeze nothing lifts them away from their stops."
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    calm_shorts = share_neg <= 0.10
    lo = C.rolling(720, min_periods=720).min()
    base = (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480)) & (C <= lo * 1.05)
    return base.mul(calm_shorts, axis=0).astype(bool)
