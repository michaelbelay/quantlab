"""Bull flag after a pump (discovery 2026-10-12).
Idea: in an uptrend, a coin made a >= 3 sigma 24h pump 24-72h ago, still holds within 1 sigma of the high since then,
moves little now (|24h| <= 0.5 sigma) and its 24h volume fell below 60% of the pump's; long 48h.
Reason: after a news/flow pump, holders who do not sell on falling volume show the move is not being distributed;
buyers who missed the first leg step in on the second. Repeats with every narrative pump in a bull market."""
NAME = "Bull flag (UP, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 1.5, "UP"


def signals(g):
    pumped = (g.ret24 >= 3 * g.sigma).astype(float).shift(24).rolling(48).max() > 0
    top = g.high.rolling(72).max()
    held = g.close >= top * (1 - g.sigma)
    quiet = (g.ret24.abs() <= 0.5 * g.sigma) & (g.vol24 <= 0.6 * g.vol24.rolling(72).max())
    m = pumped & held & quiet & (g.close > g.sma480)
    return m & ~m.shift(1, fill_value=False)
