"""Leader pullback in a calm bear (discovery 2026-11-16).
Idea: on calm downtrend days (DN_LOVOL), a coin up >= 10% over 7 days while BTC moved less than 5% either way over
the same week, above its EMA100 and its 20-day average, on the first hour its 24h return is <= -2% (a pullback),
is bought for 48h (stop 1.5 sigma).
Reason: in a quiet bear most coins drift and capital crowds into the few coins with a live story (the only game in
town); the pullback is profit-taking by early longs and shorts leaning on the bear, and the story traders who missed
the first leg buy it. Not dip-buying into a crash: BTC must be calm and the coin must be in an uptrend of its own."""
NAME = "Calm-bear leader pullback (DN_LOVOL, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 1.5, "DN_LOVOL"


def _btc(g, s):
    b = s[(g.coin == "BTC").to_numpy()]
    b.index = g.date[(g.coin == "BTC").to_numpy()]
    return g.date.map(b)


def signals(g):
    b7 = _btc(g, g.ret168)
    m = (g.ret168 >= 0.10) & (b7.abs() <= 0.05) & (g.close > g.ema100) & (g.close > g.sma480) & (g.ret24 <= -0.02) \
        & (g.coin != "BTC")
    return m & ~m.shift(1, fill_value=False)
