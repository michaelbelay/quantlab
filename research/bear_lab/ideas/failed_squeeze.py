"""A short squeeze (1h +3% with OI -2% in the same hour) in the last 48h has fully round-tripped: close is back under the
pre-squeeze close, under the 480h EMA. Short the first such bar. Written 2026-11-02 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 48
REASON = "A squeeze clears out the shorts; if price still falls back under the pre-squeeze level there were no real buyers, and with no shorts left to cover nothing slows the drop."
def signals(P):
    C, OI = P["C"], P["OI"]
    e = bl.ema(C, 480)
    sq = (C / C.shift(1) - 1 >= 0.03) & (OI / OI.shift(1) - 1 <= -0.02)
    pre = C.shift(1).where(sq).ffill(limit=48)
    recent = sq.astype(float).rolling(48, min_periods=1).max() > 0
    sig = recent & (C < pre) & (C < e)
    return sig & ~sig.shift(1, fill_value=False)
