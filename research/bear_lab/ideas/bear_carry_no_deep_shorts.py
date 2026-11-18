"""Any bear day: at a funding settlement the coin pays >= +0.01%, is under its 72h EMA, and no coin of the 19 has a
last funding <= -0.01% (a short crowd big enough that shorts pay the full default-size rate). The market filter is
measured by depth of the negative rate instead of the count of negative coins: slightly negative prints (-0.001%) are
noise, not a crowd. Written 2026-11-16 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "A squeeze needs a short crowd that is paying to stay short; a book barely below zero has no such crowd, so a coin under its three-day trend whose longs pay full funding has nobody to lift it off its lows."
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    no_deep_shorts = (FL <= -0.0001).sum(axis=1) == 0
    base = (P["FUND"] >= 0.0001) & (C < bl.ema(C, 72))
    return base.mul(no_deep_shorts, axis=0).astype(bool)
