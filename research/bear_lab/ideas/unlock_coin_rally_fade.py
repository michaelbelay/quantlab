"""Coins with heavy ongoing token unlocks / emissions (ARB, SUI, WLD, ENA, PUMP, TAO): on a bear day, a 72h rally
of >= 10% that is still under the 480h EMA is shorted. Written 2026-11-02 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.10, None, 72
REASON = "Unlock recipients, miners and airdrop farmers must sell supply and use rallies in a weak market as exit liquidity."
SUPPLY = ["ARB", "SUI", "WLD", "ENA", "PUMP", "TAO"]
def signals(P):
    C = P["C"]
    e = bl.ema(C, 480)
    sig = (C / C.shift(72) - 1 >= 0.10) & (C < e)
    for c in C.columns:
        if c not in SUPPLY:
            sig[c] = False
    return sig
