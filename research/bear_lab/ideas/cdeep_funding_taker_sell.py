"""cdeep_funding while the coin's 24h average taker buy/sell ratio is < 0.95 (aggressive sellers dominate).
Written 2026-11-11 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Longs still pay funding while market sellers hit bids all day: someone is unloading into a long book that has not given up yet."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    tk = P["TAKER"].rolling(24, min_periods=20).mean()
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480)) & (tk < 0.95)
