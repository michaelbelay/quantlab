"""Any bear day: at most 10% of the 19 coins have negative last funding, the coin is under its 480h EMA and closes under
its prior 72h low. No deep-bear filter and no own-funding condition. Written 2026-11-12 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "A 3-day low break fires long stops; with no coin paying negative funding there are no crowded shorts to squeeze the break back, so the move runs."
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    calm_shorts = share_neg <= 0.10
    low72 = C.rolling(72, min_periods=72).min().shift(1)
    base = (C < bl.ema(C, 480)) & (C < low72)
    return base.mul(calm_shorts, axis=0).astype(bool)
