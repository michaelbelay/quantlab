"""Crowded shorts against a rising coin (discovery 2026-10-12).
Idea: in an uptrend, a coin above its 20-day average and up > 5% over 7 days has negative funding in its bottom 10%
(90-day percentile); long 48h.
Reason: shorts are paying to fight a coin that keeps rising; as price grinds up they are forced to cover (stops and
liquidations are buy orders). Repeats whenever traders try to call the top of a trending coin."""
NAME = "Negative funding squeeze (UP, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 1.5, "UP"


def signals(g):
    m = (g.fund_last < 0) & (g.fund_pct <= 0.1) & (g.close > g.sma480) & (g.ret168 > 0.05)
    return m & ~m.shift(1, fill_value=False)
