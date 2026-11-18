"""Any bear day: at a funding settlement the coin pays >= +0.01%, is under its 480h EMA, and at least two thirds of the
19 coins have a last funding >= +0.01% (the market's longs pay the full default rate). A positive definition of "no
short crowd" instead of counting negative coins. Written 2026-11-13 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "When most perp books lean long enough that their longs pay the full rate, shorts are the scarce side; there is nobody to squeeze, and the paying longs are the ones who must fold."
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_pay = (FL >= 0.0001).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    payers_majority = share_pay >= 2 / 3
    base = (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480))
    return base.mul(payers_majority, axis=0).astype(bool)
