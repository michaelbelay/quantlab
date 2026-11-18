"""Any bear day: at a funding settlement the coin pays >= +0.01% and is under its 480h EMA, while EITHER at most 10% of
the 19 coins have negative last funding OR BTC's last funding is >= +0.01%. Union of the two market filters that passed
on 2026-11-12/13 (bear_carry_no_shorts, bear_carry_btc_default), written for frequency. Written 2026-11-14 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "The market's short hedges sit either spread across alt perps or concentrated in BTC perps; when either book shows no shorts, the longs paying full funding under their trend are the only side that gets forced out."
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    thin_hedge = (share_neg <= 0.10) | (FL["BTC"] >= 0.0001)
    base = (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480))
    return base.mul(thin_hedge, axis=0).astype(bool)
