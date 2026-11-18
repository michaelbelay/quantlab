"""Cross-coin lead/lag on BTC relief jumps in a bear (discovery 2026-11-09).
Idea: in a falling market (DN), BTC rises >= 1.5% in one hour; alts that rose less than a third of that in the same
hour are bought for 6h (stop 1 sigma).
Reason: a sharp BTC jump in a bear is short covering; market makers re-hedge alt books off BTC with a delay and alt
shorts get squeezed in turn, so laggards catch up within hours. Not dip-buying: it follows a BTC up-move."""
NAME = "BTC bounce laggards (DN, long 6h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 6, 1.0, "DN"


def _btc(g, s):
    b = s[(g.coin == "BTC").to_numpy()]
    b.index = g.date[(g.coin == "BTC").to_numpy()]
    return g.date.map(b)


def signals(g):
    r1 = g.close / g.close.shift(1) - 1
    br1 = _btc(g, r1)
    return (br1 >= 0.015) & (r1 < br1 / 3) & (g.coin != "BTC")
