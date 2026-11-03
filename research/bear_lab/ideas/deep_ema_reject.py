"""Deep bear: a coin bounces >= 5% in 72h, tags its falling 480h EMA from below and closes back under it on a red bar.
Short the rejection at the moving average. Written 2026-11-02 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "In a deep bear, holders trapped above the falling 20-day EMA sell at break-even when the bounce reaches it."
def signals(P):
    C, O, Hh = P["C"], P["O"], P["H"]
    e = bl.ema(C, 480)
    deep = pd.DataFrame({c: P["DEEP"] for c in C.columns})
    bounce = C / C.shift(72) - 1 >= 0.05
    tag = (Hh >= e * 0.995) & (C < e) & (C < O)
    falling = e < e.shift(168)
    return deep & bounce & tag & falling
