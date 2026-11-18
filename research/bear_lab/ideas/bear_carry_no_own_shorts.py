"""Any bear day: at a funding settlement the coin pays >= +0.01%, is under its 480h EMA, and none of its own settlements
in the last 7 days was negative. Coin-level "no short crowd" instead of the market-wide filter, so coins qualify on
their own days. Written 2026-11-13 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "A coin whose funding never went negative for a week has no short crowd in it; its longs have been paying the whole time and are the only side that can be forced out."
def signals(P):
    C, F = P["C"], P["FUND"]
    no_own_shorts = F.rolling(168, min_periods=3).min() >= 0
    return (F >= 0.0001) & (C < bl.ema(C, 480)) & no_own_shorts
