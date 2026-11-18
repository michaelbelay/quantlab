"""cdeep_funding signal only if the coin had no +15% 72h rally in the last 14 days.
A recent squeeze means squeeze traders are active in the coin. Written 2026-11-05 by the daily agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bear_lab as bl
import pandas as pd
SIDE, HOLD, STOP, TARGET, GAP = -1, 72, 0.08, None, 72
REASON = "Coins that squeezed in the last two weeks still hold squeeze traders who hunt shorts; coins with no squeeze are left to bleed by paying longs."
def coin_deep(C):
    s = C.rolling(4800, min_periods=4800).mean()
    return (C < s) & (s < s.shift(480))
def signals(P):
    C = P["C"]
    r72 = C / C.shift(72) - 1
    squeezed = r72.rolling(336, min_periods=336).max() >= 0.15
    return coin_deep(C) & (P["FUND"] >= 0.0001) & (C < bl.ema(C, 480)) & ~squeezed & r72.notna()
