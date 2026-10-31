"""Cross-coin lead/lag, down side (discovery 2026-10-07).
Idea: in a falling market (BTC below its 50-day average), BTC drops >= 1.5% in one hour; alts that fell less than a
third of that in the same hour are shorted for 6h.
Reason: alt bids are pulled with a delay (market makers re-hedge off BTC, stops and liquidations on alts trigger
later), so laggards catch down; repeats on every sharp BTC drop."""
import numpy as np

NAME = "BTC dump laggards (DN, short 6h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = -1, 6, 1.0, "DN"


def _btc(g, s):
    b = s[(g.coin == "BTC").to_numpy()]
    b.index = g.date[(g.coin == "BTC").to_numpy()]
    return g.date.map(b)


def signals(g):
    r1 = g.close / g.close.shift(1) - 1
    br1 = _btc(g, r1)
    return (br1 <= -0.015) & (r1 > br1 / 3) & (g.coin != "BTC")
