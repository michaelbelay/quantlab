"""cdeep_funding signal only on the 8 large caps (BTC ETH BNB SOL XRP LINK ADA DOGE).
Large holder bases unwind slowly; thin-float alts get squeezed. Written 2026-11-05 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Large caps in their own bear have a wide holder base that sells for weeks; squeezes that kill shorts happen in thin-float alts (ENA, ZEC), not here."
MAJORS = ["BTC", "ETH", "BNB", "SOL", "XRP", "LINK", "ADA", "DOGE"]
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    sig = coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480))
    keep = pd.Series([c in MAJORS for c in C.columns], index=C.columns)
    return sig & keep
