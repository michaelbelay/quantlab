"""Relative strength during a sell-off (discovery 2026-10-07).
Idea: in a falling market (BTC below its 50-day average) with BTC down >= 5% over 7 days, coins that are UP over the same
7 days are bought at 00:00 UTC for 72h.
Reason: a coin that rises while the market falls has a persistent buyer (accumulation, buybacks, a real story) that
absorbs the market-wide selling; when the selling eases, that buyer is still there. Repeats in every sell-off."""
NAME = "Resilient coins in sell-offs (DN, long 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 72, 2.0, "DN"


def _btc(g, s):
    b = s[(g.coin == "BTC").to_numpy()]
    b.index = g.date[(g.coin == "BTC").to_numpy()]
    return g.date.map(b)


def signals(g):
    b7 = _btc(g, g.ret168)
    return (g.date.dt.hour == 23) & (b7 <= -0.05) & (g.ret168 > 0) & (g.coin != "BTC")
