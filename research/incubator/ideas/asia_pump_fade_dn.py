"""Asia-session pump fade in a bear (discovery 2026-11-16).
Idea: in a falling market (DN), at the 07:00 UTC close (end of the 00:00-08:00 Asia window), a coin below its 20-day
average that rose >= 5% over those 8 hours while BTC rose less than 1% is shorted at 08:00 for 12h (stop 1.5 sigma).
Reason: the Asia window is the thinnest part of the day for most Binance alts; a coin-only pump there is one buyer or
a bot moving a thin book. When Europe opens, market makers and bear-market sellers restock the offer and the pump
is sold back. Mirror-free: the earlier Asia idea bought dumps; this sells coin-only pumps where BTC did not join.
Who is forced: the pumper has to exit into the thicker book."""
NAME = "Asia pump fade (DN, short 12h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = -1, 12, 1.5, "DN"


def _btc(g, s):
    b = s[(g.coin == "BTC").to_numpy()]
    b.index = g.date[(g.coin == "BTC").to_numpy()]
    return g.date.map(b)


def signals(g):
    r8 = g.close / g.close.shift(8) - 1
    b8 = _btc(g, r8)
    return (g.date.dt.hour == 7) & (r8 >= 0.05) & (b8 < 0.01) & (g.close < g.sma480) & (g.coin != "BTC")
