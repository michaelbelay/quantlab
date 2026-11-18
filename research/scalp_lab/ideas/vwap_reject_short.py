"""Short a red rejection at the 24h VWAP from below in a falling coin (5m). Registered 2026-11-06, batch 1 #3."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scalp_lab as sl
SIDE, HOLD, UNIT, STOP, TARGET, GAP = -1, 24, "atr", 1.5, 2.0, 36
REASON = "trapped intraday longs sell at break-even at VWAP"
def signals(P):
    C, O, H = P["C"], P["O"], P["H"]
    vw = sl.vwap(P)
    below = (C.shift(12) < vw.shift(12)) & (C.shift(24) < vw.shift(24))
    e = sl.ema(C, 288)
    return below & (e < e.shift(12)) & (H >= vw) & (C < vw) & (C < O)
