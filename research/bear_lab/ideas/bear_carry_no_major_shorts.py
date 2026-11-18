"""Any bear day: at a funding settlement the coin pays >= +0.01%, is under its 72h EMA, and none of the 8 large caps
(BTC ETH BNB SOL XRP LINK ADA DOGE) has a negative last funding. The market filter counts only the coins where hedges
are placed; thin alts may be negative for their own reasons. Written for frequency: the 10%-of-19 filter allows at most
one negative coin of any kind. Written 2026-11-16 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "Market hedges are shorted in the large caps, not in thin alts; when no large-cap book pays shorts there is no hedge crowd to cover into a rally, so a coin under its three-day trend whose longs pay full funding bleeds on."
MAJORS = ["BTC", "ETH", "BNB", "SOL", "XRP", "LINK", "ADA", "DOGE"]
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    no_major_shorts = (FL[MAJORS] < 0).sum(axis=1) == 0
    base = (P["FUND"] >= 0.0001) & (C < bl.ema(C, 72))
    return base.mul(no_major_shorts, axis=0).astype(bool)
