"""Coin under a falling 480h EMA, OI down >= 10% in 7 days, yet funding still settles >= +0.01%.
Short the holdout longs while the market deleverages. Written 2026-11-02 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "When OI shrinks but funding stays positive, shorts are the ones leaving and longs are the holdouts paying carry; they are the remaining forced sellers as deleveraging continues."
def signals(P):
    C, F, OI = P["C"], P["FUND"], P["OI"]
    e = bl.ema(C, 480)
    return F.notna() & (F >= 0.0001) & (OI / OI.shift(168) - 1 <= -0.10) & (C < e) & (e < e.shift(168))
