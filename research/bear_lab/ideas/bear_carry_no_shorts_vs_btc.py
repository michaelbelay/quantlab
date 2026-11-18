"""Any bear day: at a funding settlement the coin pays >= +0.01%, its price in BTC (coin/BTC ratio) is under the ratio's
480h EMA (the alt is losing to BTC), while at most 10% of the 19 coins have negative last funding. The trend is measured
against BTC instead of in USD; BTC itself never fires. Written 2026-11-14 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "In 2024-26 new money buys BTC through ETFs, not alts; an alt whose longs pay full funding while it trends down against BTC is being left behind, and with no short crowd anywhere there is no rotation rally to squeeze the short."
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    calm_shorts = share_neg <= 0.10
    R = C.div(C["BTC"], axis=0)
    base = (P["FUND"] >= 0.0001) & (R < bl.ema(R, 480))
    return base.mul(calm_shorts, axis=0).astype(bool)
