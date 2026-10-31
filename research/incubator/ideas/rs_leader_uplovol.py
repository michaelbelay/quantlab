"""Relative-strength leaders in calm uptrends (discovery 2026-10-12).
Idea: on calm uptrend days (UP_LOVOL), a coin that beat BTC by > 25% over 7 days, is above its 20-day average and
closes at a new 7-day high; long 72h.
Reason: in calm bull markets money rotates into a few narrative leaders; momentum funds and late retail chase what
already leads, so leaders keep leading for days. Repeats in every quiet bull phase."""
NAME = "RS leaders (UP_LOVOL, long 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 72, 2.0, "UP_LOVOL"


def _btc(g, s):
    b = s[(g.coin == "BTC").to_numpy()]
    b.index = g.date[(g.coin == "BTC").to_numpy()]
    return g.date.map(b)


def signals(g):
    rel = g.ret168 - _btc(g, g.ret168)
    m = (rel > 0.25) & (g.close > g.sma480) & (g.close >= g.close.rolling(168).max()) & (g.coin != "BTC")
    return m & ~m.shift(1, fill_value=False)
