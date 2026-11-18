"""Any bear day: at a funding settlement the coin pays >= +0.01%, is under its 24h EMA (one day), while at most 10% of
the 19 coins have negative last funding. Next step of the trend-window series (480h -> 168h -> 72h raised the edge each
time on 2026-11-14/15); this asks where the series stops. Written 2026-11-16 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "The one-day average is where today's leveraged buyers got in; if they are already under water at the settlement and still paying, with no short crowd anywhere to squeeze for them, they are the first to be stopped out."
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    calm_shorts = share_neg <= 0.10
    base = (P["FUND"] >= 0.0001) & (C < bl.ema(C, 24))
    return base.mul(calm_shorts, axis=0).astype(bool)
