"""cdeep_funding on the 8 large caps only while the coin's own 20-day volatility is at or below its 1-year median.
Written 2026-11-09 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Squeezes that break shorts need a thin float and a volatile tape; a calm large cap in its own bear with longs paying funding just bleeds."
MAJORS = ["BTC", "ETH", "BNB", "SOL", "XRP", "LINK", "ADA", "DOGE"]
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    v = C.pct_change(fill_method=None).rolling(480, min_periods=480).std()
    calm = v <= v.rolling(8760, min_periods=4800).median()
    keep = pd.Series([c in MAJORS for c in C.columns], index=C.columns)
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480)) & calm & keep
