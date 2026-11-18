"""Any bear day (no deep-bear filter): at a funding settlement the coin's funding is >= +0.01%, the coin is under its
480h EMA, and at most 10% of the 19 coins have negative last funding (no short crowding anywhere).
Written 2026-11-12 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "Squeezes need crowded shorts; when almost no coin pays negative funding there is no squeeze fuel, so a coin under its trend whose longs pay full funding bleeds even in a shallow bear."
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    calm_shorts = share_neg <= 0.10
    base = (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480))
    return base.mul(calm_shorts, axis=0).astype(bool)
