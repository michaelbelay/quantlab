"""cdeep_funding with a 12% stop instead of 8% (same entries, same 72h hold).
Written 2026-11-11 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.12, None, 72
REASON = "2024-26 liquidation wicks hunt tight stops before the carry payers' bleed resumes; a wider stop survives the wick and keeps the bleed."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480))
