"""Deep bear: at a funding settlement the coin's funding is >= +0.01% while it sits under a falling 480h EMA.
Short and collect the carry from stubborn longs. Written 2026-11-02 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Longs still paying positive funding in a deep downtrend are bag-holders; they bleed carry to the short and capitulate on new lows."
def signals(P):
    C, F = P["C"], P["FUND"]
    e = bl.ema(C, 480)
    deep = pd.DataFrame({c: P["DEEP"] for c in C.columns})
    return deep & (F >= 0.0001) & (C < e) & (e < e.shift(168))
