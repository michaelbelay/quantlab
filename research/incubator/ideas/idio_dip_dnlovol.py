"""Coin-only dip in a calm downtrend (discovery 2026-10-26).
Idea: on calm downtrend days (DN_LOVOL), a coin down >= 2 sigma over 24h while BTC is flat or up (BTC 24h > -1%) is
bought for 24h (first hour per coin).
Reason: in a quiet market a one-coin drop without a market move is usually one large seller hitting thin books;
market makers and arbitrage desks buy it back once the order is done, and quiet markets have few follow-on sellers."""
NAME = "Coin-only dip (DN_LOVOL, long 24h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 24, 2.0, "DN_LOVOL"


def _btc(g, s):
    b = s[(g.coin == "BTC").to_numpy()]
    b.index = g.date[(g.coin == "BTC").to_numpy()]
    return g.date.map(b)


def signals(g):
    m = (g.ret24 <= -2.0 * g.sigma) & (_btc(g, g.ret24) > -0.01) & (g.coin != "BTC")
    return m & ~m.shift(1, fill_value=False)
