"""Any bear day: at a funding settlement the coin pays >= +0.01%, is under its 480h EMA, its close is below the close
24h earlier (a red day for the coin), and at most 10% of the 19 coins have negative last funding. Shallow-bear version of
cdeep_funding_weak_day. Written 2026-11-15 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "Longs paying the funding bill on a day they also lost money are the ones who sell next; a settlement on a green day lets some of them exit into strength instead."
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    calm_shorts = share_neg <= 0.10
    base = (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480)) & (C < C.shift(24))
    return base.mul(calm_shorts, axis=0).astype(bool)
