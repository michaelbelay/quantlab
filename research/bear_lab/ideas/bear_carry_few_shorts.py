"""Any bear day: at a funding settlement the coin pays >= +0.01%, is under its 480h EMA, and at most 20% of the 19
coins (3 coins) have negative last funding. Threshold variant of bear_carry_no_shorts (10%) written for frequency.
Written 2026-11-13 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "A market squeeze needs shorts across the board; two or three crowded coins cannot lift the whole market, so longs paying full funding under their trend still bleed."
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    few_shorts = share_neg <= 0.20
    base = (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480))
    return base.mul(few_shorts, axis=0).astype(bool)
