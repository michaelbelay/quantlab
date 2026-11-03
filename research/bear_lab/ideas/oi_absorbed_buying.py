"""Taker buying at a 30-day high (24h mean) but the price did not rise in those 24h, under the 480h EMA.
Written 2026-11-02 (main session, OI round 3)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 48, 0.07, None, 48
REASON = "Market buys soaked up by passive sellers show a large seller distributing; when the buyers stop, price drops."
def signals(P):
    C = P["C"]
    tk = P["TAKER"].rolling(24, min_periods=24).mean()
    return (bl.rank_prev(tk) >= 0.90) & (C / C.shift(24) - 1 <= 0) & (C < bl.ema(C, 480))
