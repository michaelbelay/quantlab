"""Downtrend coin whose funding was <= -0.01% in the last 72h now settles at >= 0 again (shorts have covered).
Short the resumed trend once the squeeze fuel is gone. Written 2026-11-02 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Negative funding marks crowded shorts (squeeze fuel); once funding is back >= 0 they have covered, the bid from covering is gone and trend sellers face no squeeze."
def signals(P):
    C, F = P["C"], P["FUND"]
    e = bl.ema(C, 480)
    was_neg = (F <= -0.0001).astype(float).rolling(72, min_periods=1).max() > 0
    return F.notna() & (F >= 0) & was_neg & (C < e) & (e < e.shift(168))
