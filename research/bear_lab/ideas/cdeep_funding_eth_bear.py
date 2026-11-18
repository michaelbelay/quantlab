"""cdeep_funding only while ETH is also in its own deep bear (under a falling 200-day average).
Written 2026-11-10 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "In 2024-26 BTC has its own ETF bid but alts trade off ETH; with ETH in its own bear there is no alt-rotation bid to squeeze carry shorts."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    d = coin_deep(C)
    base = d & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480))
    return base.mul(d["ETH"], axis=0).astype(bool)
