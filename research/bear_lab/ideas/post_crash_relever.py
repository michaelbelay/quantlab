"""After a BTC crash (-10% over 7 days at some point in the last 7 days), short a coin whose OI is back above its level
of 7 days ago while its price is still >= 10% under its 14-day high. Written 2026-11-06 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "After a crash, dip buyers re-lever fast (OI fully back) while price has not recovered; those new longs are the fuel for the second leg (2025-03, 2025-10/11)."
def signals(P):
    C = P["C"]
    btc = C["BTC"]
    crash = (btc / btc.shift(168) - 1).rolling(168, min_periods=168).min() <= -0.10
    K = pd.DataFrame({c: crash for c in C.columns}, index=C.index)
    OI = P["OI"]
    relever = OI >= OI.shift(168)
    still_down = C <= 0.90 * C.rolling(336, min_periods=336).max()
    return K & relever & still_down & (C < bl.ema(C, 480))
