"""Any bear day: at a funding settlement the coin pays >= +0.01% while at most 10% of the 19 coins have negative last
funding. No trend condition (control for the EMA480 filter in bear_carry_no_shorts), so every paying coin can enter on
every no-shorts bear day. Written 2026-11-14 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "On a bear day with no shorts anywhere, longs paying full funding are the only leveraged side left; they get forced out whether or not the coin already sits under its 20-day average."
def signals(P):
    FL = P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    calm_shorts = share_neg <= 0.10
    base = P["FUND"] >= 0.0001
    return base.mul(calm_shorts, axis=0).astype(bool)
