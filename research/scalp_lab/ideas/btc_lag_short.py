"""Short a coin that has not yet followed a fast BTC drop (5m). Registered 2026-11-06, batch 1 #2."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scalp_lab as sl
SIDE, HOLD, UNIT, STOP, TARGET, GAP = -1, 12, "pct", 0.010, 0.008, 12
REASON = "alts reprice after BTC with a lag as market makers hedge"
def signals(P):
    C = P["C"]
    r3 = C / C.shift(3) - 1
    btc_drop = r3["BTC"] <= -0.006
    sig = (r3 > -0.002).apply(lambda s: s & btc_drop)
    sig["BTC"] = False
    return sig
