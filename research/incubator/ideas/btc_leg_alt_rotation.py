"""BTC leg pauses, money rotates into alts (discovery 2026-10-12).
Idea: BTC is up >= 8% over 7 days but flat (|24h| <= 1%) now; alts still above their 20-day average that lagged
BTC's week by > 3 points are bought for 72h. Uptrend days only.
Reason: after a BTC leg, profits rotate down the risk curve into alts (the classic "BTC first, alts next" flow);
it repeats because the same traders take BTC profit and look for the cheaper catch-up trade."""
NAME = "BTC leg -> alt rotation (UP, long 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 72, 2.0, "UP"


def _btc(g, s):
    b = s[(g.coin == "BTC").to_numpy()]
    b.index = g.date[(g.coin == "BTC").to_numpy()]
    return g.date.map(b)


def signals(g):
    b7, b1 = _btc(g, g.ret168), _btc(g, g.ret24)
    m = (b7 >= 0.08) & (b1.abs() <= 0.01) & (g.ret168 < b7 - 0.03) & (g.close > g.sma480) & (g.coin != "BTC")
    return m & ~m.shift(1, fill_value=False)
