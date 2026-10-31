"""Market-wide breadth thrust (discovery 2026-10-07).
Idea: in an uptrend, the first hour in which >= 70% of coins are up > 3% over 24h; buy every coin that is up > 3%,
hold 72h.
Reason: a broad, simultaneous rise means new money / short covering across the whole market, not one story; trend
followers and late buyers keep adding for days after such a thrust, and it repeats at the start of most alt rallies."""
import numpy as np

NAME = "Breadth thrust (UP, long 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 72, 2.0, "UP"


def signals(g):
    up = (g.ret24 > 0.03).where(g.ret24.notna())
    share = up.groupby(g.date).mean().sort_index()
    first = (share >= 0.7) & (share.shift(1) < 0.7)
    return g.date.map(first).fillna(False).astype(bool) & (g.ret24 > 0.03)
