"""Funding flip from negative to positive (discovery 2026-11-02).
Idea: in an uptrend (UP), a coin above its 20-day average whose funding is positive now but was negative 24h and 48h ago
is bought for 48h (first hour per coin).
Reason: a flip means the short crowd that paid funding for days has covered (forced buying done) and new longs accept
paying to hold; the trend has switched sides of the leverage book, and late shorts still left get squeezed."""
NAME = "Funding flip (UP, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 1.5, "UP"


def signals(g):
    m = (g.fund_last > 0) & (g.fund_last.shift(24) < 0) & (g.fund_last.shift(48) < 0) & (g.close > g.sma480)
    return m & ~m.shift(1, fill_value=False)
