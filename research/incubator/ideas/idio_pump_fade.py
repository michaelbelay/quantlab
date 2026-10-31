"""Fade a one-coin pump while the market is flat (discovery 2026-10-07).
Idea: a coin rises >= 4 hourly sigmas in one hour on >= 5x its normal hourly volume while BTC moved < 0.5% that hour;
short for 12h.
Reason: a coin-only spike with a flat market is usually one aggressive buyer or a thin-book squeeze, not news the whole
market prices; once that buyer stops, market makers and arbitrageurs refill the book and price gives part of it back."""
import numpy as np

NAME = "Idiosyncratic pump fade (short 12h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = -1, 12, 1.0, None


def _btc(g, s):
    b = s[(g.coin == "BTC").to_numpy()]
    b.index = g.date[(g.coin == "BTC").to_numpy()]
    return g.date.map(b)


def signals(g):
    r1 = g.close / g.close.shift(1) - 1
    br1 = _btc(g, r1)
    hs = g.sigma / np.sqrt(24)
    vol_x = g.volume / (g.vol24_avg30 / 24)
    m = (r1 >= 4 * hs) & (vol_x >= 5) & (br1.abs() < 0.005) & (g.coin != "BTC")
    return m & ~m.shift(1, fill_value=False)
