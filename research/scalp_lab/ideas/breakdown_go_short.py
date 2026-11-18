"""Short a high-volume close below the prior 4h low (5m). Registered 2026-11-06, batch 1 #4."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scalp_lab as sl
SIDE, HOLD, UNIT, STOP, TARGET, GAP = -1, 24, "atr", 1.2, 2.0, 24
REASON = "stops under the 4h low fire in a cascade"
def signals(P):
    C, H, L, V = P["C"], P["H"], P["L"], P["V"]
    lo48 = L.shift(1).rolling(48, min_periods=48).min()
    vol = V >= 3 * V.shift(1).rolling(288, min_periods=288).mean()
    return (C < lo48) & vol & ((C - L) <= 0.25 * (H - L)) & (C < sl.vwap(P))
