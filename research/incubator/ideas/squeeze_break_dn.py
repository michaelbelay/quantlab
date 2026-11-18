"""Short squeeze breakout in a bear (discovery 2026-11-09).
Idea: in a falling market (DN), a coin with negative funding (shorts paying) that closes above its highest high of the
previous 72 hours on 24h volume >= 1.5x its 30-day average is bought for 24h (first hour, stop 1.5 sigma).
Reason: the shorts' stops sit above the recent highs; a break through them on volume forces buy-to-cover orders, and
shorts who pay funding have no reason to wait. Not dip-buying: it buys strength that shorts are forced to chase."""
NAME = "Squeeze breakout (DN, long 24h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 24, 1.5, "DN"


def signals(g):
    hi72 = g.high.shift(1).rolling(72).max()
    m = (g.close > hi72) & (g.fund_last < 0) & (g.vol24 >= 1.5 * g.vol24_avg30)
    return m & ~m.shift(1, fill_value=False)
