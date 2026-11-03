"""Deep bear: a coin bounces >= 6% in 72h while open interest grows >= 8%, still under its 50-day average.
New leveraged longs chase the bounce; short it. Written 2026-11-02 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "Longs who add leverage into a deep-bear bounce have no spot bid behind them and get liquidated on the next leg down."
def signals(P):
    C, OI = P["C"], P["OI"]
    deep = pd.DataFrame({c: P["DEEP"] for c in C.columns})
    sma50d = C.rolling(1200, min_periods=1200).mean()
    bounce = C / C.shift(72) - 1 >= 0.06
    oi_up = OI / OI.shift(72) - 1 >= 0.08
    return deep & bounce & oi_up & (C < sma50d)
