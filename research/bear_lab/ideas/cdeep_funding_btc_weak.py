"""cdeep_funding signal only while BTC closes under its own 168h EMA (BTC weak this week too).
Alt squeezes mostly ride BTC rallies. Written 2026-11-06 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Alt shorts get squeezed by BTC-led rallies; when BTC itself trades under its weekly trend there is no market bid to lift a coin whose longs still pay funding."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    btc = C["BTC"]
    w = btc < bl.ema(C[["BTC"]], 168)["BTC"]
    W = pd.DataFrame({c: w for c in C.columns}, index=C.index)
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480)) & W
