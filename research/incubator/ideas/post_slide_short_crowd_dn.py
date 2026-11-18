"""Short crowd after a week-long slide, BTC stabilises (discovery 2026-11-16).
Idea: in a falling market (DN), a coin (not BTC) down >= 15% over 7 days with negative last funding, on the first
hour BTC is up over 24h and no worse than -2% over 72h (the market has stopped falling), is bought for 72h
(stop 2 sigma).
Reason: after a week-long slide the shorts are late and crowded (negative funding = they pay to stay). Their trade
needs BTC to keep falling; once BTC stabilises for three days, the alt's shorts have no market tailwind and cover
into a thin bid, which lifts the beaten coin more than BTC. Not plain dip-buying: the trigger is market
stabilisation plus a paying short crowd, and the stop cuts a renewed BTC leg down."""
NAME = "Post-slide short crowd (DN, long 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 72, 2.0, "DN"


def _btc(g, s):
    b = s[(g.coin == "BTC").to_numpy()]
    b.index = g.date[(g.coin == "BTC").to_numpy()]
    return g.date.map(b)


def signals(g):
    r72 = g.close / g.close.shift(72) - 1
    b24, b72 = _btc(g, g.ret24), _btc(g, r72)
    m = (g.ret168 <= -0.15) & (g.fund_last < 0) & (b24 >= 0) & (b72 >= -0.02) & (g.coin != "BTC")
    return m & ~m.shift(1, fill_value=False)
