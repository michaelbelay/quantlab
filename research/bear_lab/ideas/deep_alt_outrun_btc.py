"""Deep bear: an alt beats BTC by >= 8 points over 72h while still under its own 50-day average.
Short the lone pump that has no market behind it. Written 2026-11-02 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 24
REASON = "In a deep bear there is no broad bid; a single-coin pump is short squeezes and news chasers who sell once BTC fails to follow."
def signals(P):
    C = P["C"]
    r = C / C.shift(72) - 1
    rel = r.sub(r["BTC"], axis=0)
    sma50d = C.rolling(1200, min_periods=1200).mean()
    deep = pd.DataFrame({c: P["DEEP"] for c in C.columns})
    sig = deep & (rel >= 0.08) & (C < sma50d)
    sig["BTC"] = False
    return sig
