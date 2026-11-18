"""Any bear day: at a funding settlement the coin pays >= +0.01%, is under its 480h EMA, at least 60% of the 19 coins
are under their own 480h EMA (sector-wide downtrend), and at most 10% of the 19 coins have negative last funding.
Shallow-bear version of cdeep_funding_breadth. Written 2026-11-15 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "When most of the sector is under trend there is no rotation bid moving from coin to coin; longs paying funding on a coin under trend get no rescue from a neighbour's rally, and with no short crowd anywhere nothing squeezes."
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    calm_shorts = share_neg <= 0.10
    under = C < bl.ema(C, 480)
    share_under = under.sum(axis=1) / C.notna().sum(axis=1).clip(lower=1)
    wide = calm_shorts & (share_under >= 0.60)
    base = (P["FUND"] >= 0.0001) & under
    return base.mul(wide, axis=0).astype(bool)
