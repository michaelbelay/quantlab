"""Deep bear: a coin under a falling 480h EMA whose 7-day realised volatility is in the lowest tenth of its last 30 days.
Short the quiet grind before the next liquidation leg. Written 2026-11-02 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 168, 0.10, None, 72
REASON = "Quiet weeks in a deep bear mean buyers are gone, leverage rebuilds and stops cluster; the next move is a flush, not a bounce."
def signals(P):
    C = P["C"]
    e = bl.ema(C, 480)
    vol = C.pct_change(fill_method=None).rolling(168, min_periods=150).std()
    vol_d = vol[vol.index.hour == 23]
    rk = bl.rank_prev(vol_d, 30).reindex(C.index)
    deep = pd.DataFrame({c: P["DEEP"] for c in C.columns})
    return deep & (rk <= 0.10) & (C < e) & (e < e.shift(168))
