"""Any bear day (no deep-bear filter): coin under its 480h EMA while at most 10% of the 19 coins have negative last
funding; no own-funding condition, once a day at 23:00 UTC. Shallow-bear version of cdeep_calm_shorts_trend.
Written 2026-11-13 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Squeezes need crowded shorts; when almost no coin pays negative funding there is no squeeze fuel, so a coin under its trend bleeds even in a shallow bear, whatever its own funding."
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    calm_shorts = (share_neg <= 0.10) & pd.Series(P["INDEX"].hour == 23, index=P["INDEX"])
    base = C < bl.ema(C, 480)
    return base.mul(calm_shorts, axis=0).astype(bool)
