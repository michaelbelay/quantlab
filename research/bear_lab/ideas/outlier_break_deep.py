"""Deep bear: an alt that beat BTC by >= 15 points over 30 days closes under its 168h EMA (first cross).
Short the outlier once its momentum breaks; it catches down to the market. Written 2026-11-02 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 168, 0.10, None, 168
REASON = "In a deep bear a coin that held up draws the last momentum longs; when its trend breaks they exit together and holders rotate to cash, so it catches down to the market."
def signals(P):
    C = P["C"]
    r30 = C / C.shift(720) - 1
    rel = r30.sub(r30["BTC"], axis=0)
    e = bl.ema(C, 168)
    cross = (C < e) & (C.shift(1) >= e.shift(1))
    deep = pd.DataFrame({c: P["DEEP"] for c in C.columns})
    return deep & (rel >= 0.15) & cross
