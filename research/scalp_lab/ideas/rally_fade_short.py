"""Short the first breakdown bar after a sharp 1h rally in a coin that is down on the day (5m). Registered 2026-11-06, batch 1 #5."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scalp_lab as sl
SIDE, HOLD, UNIT, STOP, TARGET, GAP = -1, 36, "atr", 2.0, 2.0, 36
REASON = "bear rallies are short covering; when covering stops there is no buyer"
def signals(P):
    C, O, L = P["C"], P["O"], P["L"]
    r12 = C / C.shift(12) - 1
    r288 = C / C.shift(288) - 1
    return (r12.shift(1) >= 0.025) & (r288 < 0) & (sl.rsi(C, 14).shift(1) >= 75) & (C < O) & (C < L.shift(1))
