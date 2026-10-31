"""Funding reset in an uptrend (discovery 2026-10-12).
Idea: in an uptrend, a coin whose funding was in its top 10% (90-day percentile) within the last 72h drops to its
bottom 30% while price stays above the 20-day average and up over 7 days; long 48h.
Reason: the leveraged longs were flushed out (funding resets) but the trend itself held, so spot/trend buyers face
less overhead leverage to unwind; it repeats after every leverage washout inside a bull leg."""
NAME = "Funding reset (UP, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 1.5, "UP"


def signals(g):
    was_hot = (g.fund_pct >= 0.9).astype(float).rolling(72).max() > 0
    m = was_hot & (g.fund_pct <= 0.3) & (g.close > g.sma480) & (g.ret168 > 0)
    return m & ~m.shift(1, fill_value=False)
