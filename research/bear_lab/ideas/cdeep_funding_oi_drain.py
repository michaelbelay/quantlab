"""Coin in its own deep bear, funding >= +0.01%, under its 480h EMA, while OI fell >= 5% and price fell over 72h.
Longs are liquidating and no new shorts are building, so no squeeze fuel. Written 2026-11-05 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Falling price with falling OI and positive funding is long liquidation, not short building: longs keep exiting and there are no shorts to squeeze."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C, OI = P["C"], P["OI"]
    drain = (OI / OI.shift(72) - 1 <= -0.05) & (C / C.shift(72) - 1 < 0)
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480)) & drain
