"""Any bear day: at a funding settlement the coin pays >= +0.01%, is under its 480h EMA, and BTC's last funding is also
>= +0.01% (nobody is short-hedging the market through BTC). Shallow-bear version of cdeep_funding_btc_default; a
single-coin market filter, so it should hold on more days than the 10%-negative count. Written 2026-11-13 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "BTC perps are where the market hedges short; while BTC longs still pay the full rate there is no hedge book to cover into a rally, so alt longs paying under their trend bleed on."
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    btc_default = FL["BTC"] >= 0.0001
    base = (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480))
    return base.mul(btc_default, axis=0).astype(bool)
