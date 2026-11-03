"""Low-volume bounce in a downtrend (discovery 2026-11-02).
Idea: in a falling market (DN), a coin below its 20-day average that bounced > 1.5 sigma in 24h on below-average volume
(24h volume < 0.8x its 30-day mean) is shorted for 48h (first hour per coin).
Reason: a bounce without volume is shorts taking profit, not new buyers; once covering is done, the trapped holders
from higher up sell into the bounce again, and it repeats in every bear leg."""
NAME = "Low-volume bounce (DN, short 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = -1, 48, 1.5, "DN"


def signals(g):
    m = (g.close < g.sma480) & (g.ret24 > 1.5 * g.sigma) & (g.vol24 < 0.8 * g.vol24_avg30)
    return m & ~m.shift(1, fill_value=False)
