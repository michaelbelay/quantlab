"""cdeep_funding signal only while the coin is at most 35% under its 200-day high (early bear, not yet broken).
Holders have not capitulated yet; broken coins (-50%) already sold and get squeezed. Written 2026-11-05 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Early in a coin's own bear the holder base is still full and sells into weakness; deep-underwater coins have no sellers left and squeeze (cdeep_broken_coin lost)."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    dd = 1 - C / C.rolling(4800, min_periods=4800).max()
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480)) & (dd <= 0.35)
