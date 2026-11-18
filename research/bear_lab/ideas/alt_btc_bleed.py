"""Alt whose coin/BTC ratio is under its falling 200-day average and still falling over 7 days, coin under its 480h EMA.
Checked once a day at the 00:00 close, no funding condition. Written 2026-11-07 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "In 2024-26 the new money (ETFs, treasuries) bids only BTC while alts carry unlock supply, so an alt in a long bleed against BTC has sellers and no rotation buyer."
def signals(P):
    C, I = P["C"], P["INDEX"]
    R = C.div(C["BTC"], axis=0)
    s = R.rolling(4800, min_periods=4800).mean()
    bleed = (R < s) & (s < s.shift(480)) & (R < R.shift(168))
    d = pd.DataFrame({c: I.hour == 0 for c in C.columns}, index=I)
    m = bleed & (C < bl.ema(C, 480)) & d
    m["BTC"] = False
    return m
