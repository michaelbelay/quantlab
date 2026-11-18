"""Any bear day, 8 large caps only (BTC ETH BNB SOL XRP LINK ADA DOGE): at a funding settlement the coin pays >= +0.01%,
is under its 480h EMA, while at most 10% of the 19 coins have negative last funding. Shallow-bear version of
cdeep_majors_no_shorts. Written 2026-11-14 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "Large caps have a wide holder base that sells for weeks and no thin float to squeeze; with no short crowd anywhere, their longs paying full funding under the trend bleed slowly and cleanly."
MAJORS = ["BTC", "ETH", "BNB", "SOL", "XRP", "LINK", "ADA", "DOGE"]
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    calm_shorts = share_neg <= 0.10
    base = (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480))
    keep = pd.Series([c in MAJORS for c in C.columns], index=C.columns)
    return (base.mul(calm_shorts, axis=0) & keep).astype(bool)
