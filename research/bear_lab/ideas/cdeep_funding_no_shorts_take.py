"""cdeep_funding_no_market_shorts entries with a 5% take-profit.
Written 2026-11-11 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, 0.05, 72
REASON = "No squeeze fuel market-wide lets the carry short bleed, but 2024-26 dip buyers reverse flushes within days, so bank 5%."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    base = coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480))
    return base.mul(share_neg <= 0.10, axis=0).astype(bool)
