"""Cross-coin lead/lag, up side (discovery 2026-10-07).
Idea: BTC jumps >= 1.5% in one hour; alts that moved less than a third of that in the same hour are bought for 6h.
Reason: alt quotes are hedged off BTC by market makers and retail reacts late, so laggards reprice towards BTC's move
within hours; it repeats because every BTC jump hits all books at once while alt liquidity is thin."""
import numpy as np

NAME = "BTC jump laggards (UP, long 6h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 6, 1.0, "UP"


def _btc(g, s):
    b = s[(g.coin == "BTC").to_numpy()]
    b.index = g.date[(g.coin == "BTC").to_numpy()]
    return g.date.map(b)


def signals(g):
    r1 = g.close / g.close.shift(1) - 1
    br1 = _btc(g, r1)
    return (br1 >= 0.015) & (r1 < br1 / 3) & (g.coin != "BTC")
