"""BTC drops >= 1.5% in one hour while the alt held up (alt 1h return >= BTC's + 1 pt): short the laggard for 6h.
Written 2026-11-02 (main session, round 4: timing and flow)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import numpy as np
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 6, 0.03, None, 6
REASON = "Alts follow BTC with a lag; market makers reprice alts within hours, so a laggard catches down."
def signals(P):
    C = P["C"]
    r = C / C.shift(1) - 1
    b = r["BTC"]
    lag = r.sub(b, axis=0) >= 0.01
    m = lag & pd.DataFrame({c: b <= -0.015 for c in C.columns})
    m["BTC"] = False
    return m
