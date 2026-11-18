"""Coin in its first year of trading (listed after 2022-01) under a falling 480h EMA, funding >= 0 at settlement.
New tokens carry unlock and airdrop supply. Written 2026-11-03 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "First-year tokens (ARB, SUI, WLD, ENA, TAO, HYPE, PUMP) have scheduled unlocks and airdrop holders who must sell; in a downtrend that supply meets no bid, and this holds for every 2024-26 listing."
def signals(P):
    C = P["C"]
    H = P["INDEX"]
    first = C.apply(lambda s: s.first_valid_index())
    young = pd.DataFrame({c: (pd.Series(H, index=H) - first[c] < pd.Timedelta(days=365)) & (first[c] > H[0] + pd.Timedelta(days=7))
                          if first[c] is not None else pd.Series(False, index=H) for c in C.columns})
    e = bl.ema(C, 480)
    return young & (C < e) & (e < e.shift(168)) & (P["FUND"] >= 0)
