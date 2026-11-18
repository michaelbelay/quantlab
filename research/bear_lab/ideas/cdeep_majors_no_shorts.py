"""cdeep_funding on the 8 large caps while <= 10% of the 19 coins have negative funding.
Written 2026-11-11 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Large caps have a wide holder base that sells slowly; with no shorts crowded anywhere nothing can squeeze them, so carry payers bleed."
MAJORS = ["BTC", "ETH", "BNB", "SOL", "XRP", "LINK", "ADA", "DOGE"]
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    keep = pd.Series([c in MAJORS for c in C.columns], index=C.columns)
    base = coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480)) & keep
    return base.mul(share_neg <= 0.10, axis=0).astype(bool)
