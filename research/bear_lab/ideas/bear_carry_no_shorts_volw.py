"""Any bear day: at a funding settlement the coin pays >= +0.01%, is under its 72h EMA, and the coins with a negative
last funding carry at most 10% of the 19 coins' 24h quote volume. The market filter is weighted by where the money
trades instead of counting coins, so a negative print in a thin coin does not block the day. Written 2026-11-16 by the
daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "Squeeze fuel is measured in money, not in coin count; when the books paying shorts are a sliver of traded volume there is no crowd big enough to lift the market, so a coin under its three-day trend whose longs pay full funding bleeds on."
def signals(P):
    C, QV, FL = P["C"], P["QV"], P["FUND_LAST"]
    qv24 = QV.rolling(24, min_periods=24).sum()
    neg_qv = qv24.where(FL < 0, 0.0).sum(axis=1)
    all_qv = qv24.where(FL.notna(), 0.0).sum(axis=1)
    share_neg_vol = neg_qv / all_qv.where(all_qv > 0)
    calm_shorts = share_neg_vol <= 0.10
    base = (P["FUND"] >= 0.0001) & (C < bl.ema(C, 72))
    return base.mul(calm_shorts, axis=0).astype(bool)
