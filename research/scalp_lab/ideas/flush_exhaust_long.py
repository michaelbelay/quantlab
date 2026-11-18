"""Long after a liquidation flush that closes off its low (5m). Registered 2026-11-06, batch 1 #1."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scalp_lab as sl
SIDE, HOLD, UNIT, STOP, TARGET, GAP = 1, 12, "atr", 1.5, 1.5, 24
REASON = "liquidation cascade: forced sellers are done and the wick shows buyers absorbing"
def signals(P):
    C, H, L, V, A = P["C"], P["H"], P["L"], P["V"], P["ATR"]
    drop = C.diff() <= -3 * A.shift(1)
    vol = V >= 6 * V.shift(1).rolling(288, min_periods=288).mean()
    wick = (C - L) >= 0.6 * (H - L)
    return drop & vol & wick
