"""Any bear day: at a funding settlement the coin pays >= +0.01%, is under its 72h EMA (three days), while at most 10%
of the 19 coins have negative last funding. The trend window is shortened again (480h -> 168h raised the edge on
2026-11-14); this asks whether the most recent dip buyers are the ones who sell. Written 2026-11-15 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "The three-day average is the entry price of the newest leveraged longs; when they are already under water and still paying funding, with no short crowd anywhere to squeeze for them, they are the first to cut."
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    calm_shorts = share_neg <= 0.10
    base = (P["FUND"] >= 0.0001) & (C < bl.ema(C, 72))
    return base.mul(calm_shorts, axis=0).astype(bool)
