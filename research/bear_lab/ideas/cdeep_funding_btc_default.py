"""cdeep_funding only while BTC's last settled funding is also >= 0.01% (no hedging shorts in BTC either).
Written 2026-11-11 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "BTC funding at default means nobody is short-hedging the market; with no shorts to squeeze, an alt carry short in its own bear just bleeds."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    btc_ok = P["FUND_LAST"]["BTC"] >= 0.0001
    base = coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480))
    return base.mul(btc_ok, axis=0).astype(bool)
