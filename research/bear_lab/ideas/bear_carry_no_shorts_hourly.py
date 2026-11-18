"""Any bear day, any hour: the coin's last settled funding is >= +0.01%, the coin is under its 480h EMA, and at most 10%
of the 19 coins have negative last funding. Same regime as bear_carry_no_shorts but the signal is live every hour, so a
coin re-enters as soon as its previous trade closes. Written 2026-11-13 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "The bleed of longs paying funding with no shorts to squeeze them is a regime, not an event; staying short while it holds collects it on every day, not only at the settlement hour."
def signals(P):
    C, FL = P["C"], P["FUND_LAST"]
    share_neg = (FL < 0).sum(axis=1) / FL.notna().sum(axis=1).clip(lower=1)
    calm_shorts = share_neg <= 0.10
    base = (FL >= 0.0001) & (C < bl.ema(C, 480))
    return base.mul(calm_shorts, axis=0).astype(bool)
