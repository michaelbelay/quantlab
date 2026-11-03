"""Price flat within +-3% over 7 days while OI rose >= 20%, under a falling 480h EMA.
Written 2026-11-02 (main session, OI round 3)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 96, 0.08, None, 96
REASON = "Leverage piling into a stalled coin in a downtrend resolves in the trend's direction via long liquidations."
def signals(P):
    C, OI = P["C"], P["OI"]
    e = bl.ema(C, 480)
    r7 = C / C.shift(168) - 1
    return (r7.abs() <= 0.03) & (OI / OI.shift(168) - 1 >= 0.20) & (C < e) & (e < e.shift(168))
