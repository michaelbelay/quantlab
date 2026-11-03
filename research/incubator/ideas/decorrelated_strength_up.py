"""Own-story strength (discovery 2026-11-02).
Idea: in an uptrend (UP), an alt whose 7-day hourly-return correlation with BTC is below 0.3 while it is up > 5% over
7 days and above its 20-day average is bought for 72h (first hour per coin).
Reason: a coin that rises while ignoring BTC has its own buyer (news, listing, protocol demand), not index flow;
market makers and funds that track BTC beta are slow to reprice it, so the coin-specific demand runs for days."""
NAME = "Decorrelated strength (UP, long 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 72, 2.0, "UP"


def _btc(g, s):
    b = s[(g.coin == "BTC").to_numpy()]
    b.index = g.date[(g.coin == "BTC").to_numpy()]
    return g.date.map(b)


def signals(g):
    r1 = g.close / g.close.shift(1) - 1
    corr = r1.rolling(168).corr(_btc(g, r1))
    m = (corr < 0.3) & (g.ret168 > 0.05) & (g.close > g.sma480) & (g.coin != "BTC")
    return m & ~m.shift(1, fill_value=False)
