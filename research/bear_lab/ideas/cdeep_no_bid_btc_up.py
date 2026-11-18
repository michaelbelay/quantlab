"""BTC up >= 3% in 24h but a coin in its own deep bear gained < 1% in the same 24h.
The coin cannot rally even with the market. Written 2026-11-04 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "A coin that stays flat while BTC rallies 3% has holders selling into every market bid; when BTC turns, it has no support."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    r = C / C.shift(24) - 1
    btc_up = pd.DataFrame({c: r["BTC"] >= 0.03 for c in C.columns}, index=C.index)
    sig = coin_deep(C) & btc_up & (r < 0.01) & (C < bl.ema(C, 480))
    sig["BTC"] = False
    return sig
