"""Weekend dump rebound in a bear (discovery 2026-11-09).
Idea: in a falling market (DN), at the Sunday 23:00 UTC close, a coin that fell >= 8% over the weekend (48h) while BTC
fell less than 3% is bought at Monday's open for 72h (stop 2 sigma).
Reason: weekend books are thin, so a few forced sellers (liquidations, one holder exiting) move a coin far; weekday
desks and market makers return on Monday and buy the dislocation. Not dip-buying into a crash: BTC must be calm,
so the drop is coin-only and liquidity-driven."""
NAME = "Weekend dump rebound (DN, long 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 72, 2.0, "DN"


def _btc(g, s):
    b = s[(g.coin == "BTC").to_numpy()]
    b.index = g.date[(g.coin == "BTC").to_numpy()]
    return g.date.map(b)


def signals(g):
    r48 = g.close / g.close.shift(48) - 1
    b48 = _btc(g, r48)
    sun = (g.date.dt.dayofweek == 6) & (g.date.dt.hour == 23)
    return sun & (r48 <= -0.08) & (b48 > -0.03) & (g.coin != "BTC")
