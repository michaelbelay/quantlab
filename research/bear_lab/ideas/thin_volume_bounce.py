"""Coin under a falling 480h EMA bounces >= 6% in 72h on less than 80% of the previous 72h's quote volume.
Short the first bar: a bounce without new money. Written 2026-11-02 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "A downtrend bounce on shrinking volume is shorts covering into a thin book, not new buyers; when covering ends there is no bid and trend sellers push it back down."
def signals(P):
    C, QV = P["C"], P["QV"]
    e = bl.ema(C, 480)
    v_now = QV.rolling(72, min_periods=72).sum()
    v_prev = v_now.shift(72)
    sig = (C / C.shift(72) - 1 >= 0.06) & (v_now < 0.8 * v_prev) & (C < e) & (e < e.shift(168))
    return sig & ~sig.shift(1, fill_value=False)
