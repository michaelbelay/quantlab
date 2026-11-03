"""Coin funding far above the market's (discovery 2026-11-02).
Idea: in a falling market (DN), a coin below its 20-day average and down over 7 days whose funding is > 0.03% above the
median funding of all coins at that hour is shorted for 48h (first hour per coin).
Reason: funding far above the rest of the market means one coin's longs are crowded (dip buyers on leverage) while the
market falls; they pay the short every 8h and get liquidated when the coin follows the market lower."""
NAME = "Funding spread vs market (DN, short 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = -1, 48, 1.5, "DN"


def signals(g):
    medf = g.fund_last.groupby(g.date).median()
    spread = g.fund_last - g.date.map(medf)
    m = (spread > 0.0003) & (g.close < g.sma480) & (g.ret168 < 0)
    return m & ~m.shift(1, fill_value=False)
