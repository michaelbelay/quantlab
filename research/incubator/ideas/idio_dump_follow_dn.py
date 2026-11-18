"""Coin-only dump follow-through in a bear (discovery 2026-11-16).
Idea: in a falling market (DN), a coin below its 20-day average that fell >= 8% over 24h on >= 3x its normal 24h
volume while BTC fell less than 2% (a coin-specific event: hack, unlock, delisting talk, team selling) is shorted
for 48h (stop 1.5 sigma). First hour only.
Reason: in a bull, idiosyncratic dumps get bought (idio_pump_fade/idio_dip failed before); in a bear there are no
dip buyers with spare capital, so holders who learn the news late keep selling over the following days, and market
makers widen rather than absorb. Who is forced: holders de-risking a coin with a problem while the market gives no
cover. The stop handles a squeeze."""
NAME = "Idio dump follow-through (DN, short 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = -1, 48, 1.5, "DN"


def _btc(g, s):
    b = s[(g.coin == "BTC").to_numpy()]
    b.index = g.date[(g.coin == "BTC").to_numpy()]
    return g.date.map(b)


def signals(g):
    b24 = _btc(g, g.ret24)
    m = (g.ret24 <= -0.08) & (b24 > -0.02) & (g.vol24 >= 3 * g.vol24_avg30) & (g.close < g.sma480) & (g.coin != "BTC")
    return m & ~m.shift(1, fill_value=False)
