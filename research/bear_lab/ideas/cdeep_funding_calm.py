"""cdeep_funding signal only while BTC's 20-day hourly volatility is at or below its 1-year median (calm bear).
Carry bleeds slowly when no squeeze volatility. Written 2026-11-04 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "In a calm bear, longs paying funding on a coin in its own bear bleed slowly with no squeeze to rescue them; wild bears stop out shorts."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C, F = P["C"], P["FUND"]
    r = C["BTC"].pct_change()
    v = r.rolling(480, min_periods=480).std()
    calm = v <= v.rolling(8760, min_periods=4800).median()
    calm_df = pd.DataFrame({c: calm for c in C.columns}, index=C.index)
    return coin_deep(C) & (F >= 0.0001) & (C < bl.ema(C, 480)) & calm_df
