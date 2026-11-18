"""Coin in its own deep bear pays funding >= +0.01% while the average LAST settled funding of all 19 coins is >= +0.01%.
Fix of cdeep_market_lev (its average used only coins settling that hour). Written 2026-11-04 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "When the whole market's longs still pay full funding in a bear, the deleveraging is still ahead and the weakest coin is flushed first."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C, F = P["C"], P["FUND"]
    mkt = P["FUND_LAST"].mean(axis=1) >= 0.0001
    mkt_df = pd.DataFrame({c: mkt for c in C.columns}, index=C.index)
    return coin_deep(C) & (F >= 0.0001) & mkt_df & (C < bl.ema(C, 480))
