"""Single-coin dip in a hot bull (discovery 2026-10-19).
Idea: on wild uptrend days (UP_HIVOL), a coin above its 20-day average falls >= 2 sigma over 24h while BTC's 24h
return is >= 0; long 48h (first hour the condition holds).
Reason: when the whole market is rising fast, a coin-only drop is usually one forced seller (a large liquidation or
a fund exiting) rather than news; dip buyers and momentum money, plentiful in hot markets, absorb it and price returns."""
NAME = "Idiosyncratic dip (UP_HIVOL, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 1.5, "UP_HIVOL"


def _btc(g, s):
    b = s[(g.coin == "BTC").to_numpy()]
    b.index = g.date[(g.coin == "BTC").to_numpy()]
    return g.date.map(b)


def signals(g):
    bret = _btc(g, g.ret24)
    m = (g.ret24 <= -2 * g.sigma) & (bret >= 0) & (g.close > g.sma480) & (g.coin != "BTC")
    return m & ~m.shift(1, fill_value=False)
