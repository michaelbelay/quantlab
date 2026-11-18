"""Any bear day: at a funding settlement the coin pays >= +0.01%, BTC (not the coin) is under its 72h EMA, while at most
10% of the 19 coins have negative last funding. Asks whether the trend condition the regime needs (the control without
any trend lost in half B on 2026-11-14) is the market's rather than the coin's own. Written 2026-11-16 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "In 2024-26 alts move with BTC; when BTC's newest dip buyers are under water every alt long bought with them is trapped too, and the ones still paying funding, with no short crowd anywhere to squeeze for them, must sell."
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    calm_shorts = share_neg <= 0.10
    btc_down = C["BTC"] < bl.ema(C[["BTC"]], 72)["BTC"]
    base = P["FUND"] >= 0.0001
    return base.mul(calm_shorts & btc_down, axis=0).astype(bool)
