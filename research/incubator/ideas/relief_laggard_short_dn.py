"""Relief-rally laggards in a downtrend (discovery 2026-10-19).
Idea: in a falling market, BTC rises >= 5% over 48h (relief rally); coins that are flat or down over the same 48h and
below their 20-day average are shorted for 48h (first hour per coin).
Reason: a coin that cannot rise even when BTC bounces has a seller using every bid to exit (unlocks, treasury or
distressed sales); once the relief rally ends, that seller is still there and the coin falls first."""
NAME = "Relief-rally laggards (DN, short 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = -1, 48, 1.5, "DN"


def _btc(g, s):
    b = s[(g.coin == "BTC").to_numpy()]
    b.index = g.date[(g.coin == "BTC").to_numpy()]
    return g.date.map(b)


def signals(g):
    r48 = g.close / g.close.shift(48) - 1
    br48 = _btc(g, r48)
    m = (br48 >= 0.05) & (r48 <= 0) & (g.close < g.sma480) & (g.coin != "BTC")
    return m & ~m.shift(1, fill_value=False)
