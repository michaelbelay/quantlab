"""Spot-led rally (discovery 2026-11-02).
Idea: in an uptrend (UP), a coin up > 8% over 7 days and above its 20-day average whose funding is lower than 7 days
ago and in the lower half of its 90-day range is bought for 72h (first hour per coin).
Reason: a rise without rising funding is driven by spot buyers, not leveraged longs; there is no crowded long book to
liquidate, so pullbacks are shallow and the spot demand (treasuries, funds) keeps working."""
NAME = "Spot-led rally (UP, long 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 72, 2.0, "UP"


def signals(g):
    m = (g.ret168 > 0.08) & (g.close > g.sma480) & (g.fund_last < g.fund_last.shift(168)) & (g.fund_pct <= 0.5)
    return m & ~m.shift(1, fill_value=False)
