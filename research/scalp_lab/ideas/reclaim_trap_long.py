"""Long when a fresh 24h-low breakdown is reclaimed within 6 bars (5m). Registered 2026-11-06, batch 1 #6."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scalp_lab as sl
SIDE, HOLD, UNIT, STOP, TARGET, GAP = 1, 24, "atr", 1.5, 2.0, 36
REASON = "shorts who sold the breakdown are trapped and must buy back"
def signals(P):
    C, L = P["C"], P["L"]
    lo288 = L.shift(1).rolling(288, min_periods=288).min()
    broke = L < lo288
    level = lo288.where(broke).shift(1).ffill(limit=6)
    recent = broke.shift(1).astype(float).rolling(6, min_periods=1).max().fillna(0).astype(bool)
    return recent & (C > level) & (C.shift(1) <= level)
