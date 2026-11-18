"""Any bear day: at a funding settlement the coin pays >= +0.01%, its close is under its 72h volume-weighted average
price (the actual average entry of the last three days' buyers, not a smoothed close), while at most 10% of the 19
coins have negative last funding. Written 2026-11-16 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "The three-day VWAP is the price the recent buyers actually paid; when the close sits under it every one of them is losing, and those still paying funding with no short crowd to squeeze for them sell before the bill grows."
def signals(P):
    C, V, QV, FL = P["C"], P["V"], P["QV"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    calm_shorts = share_neg <= 0.10
    vwap = QV.rolling(72, min_periods=72).sum() / V.rolling(72, min_periods=72).sum()
    base = (P["FUND"] >= 0.0001) & (C < vwap)
    return base.mul(calm_shorts, axis=0).astype(bool)
