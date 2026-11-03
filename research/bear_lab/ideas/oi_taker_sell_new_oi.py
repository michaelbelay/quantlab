"""Aggressive selling (24h taker buy/sell at a 30-day low) while OI grows >= 5% in 24h, under the 480h EMA.
Written 2026-11-02 (main session, OI round 3)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 48, 0.06, None, 48
REASON = "New shorts opening with market orders is informed, funded selling; it continues for days before covering."
def signals(P):
    C, OI = P["C"], P["OI"]
    tk = P["TAKER"].rolling(24, min_periods=24).mean()
    return (bl.rank_prev(tk) <= 0.10) & (OI / OI.shift(24) - 1 >= 0.05) & (C < bl.ema(C, 480))
