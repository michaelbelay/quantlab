"""Quiet pullback in a calm uptrend (discovery 2026-10-07).
Idea: BTC in a calm uptrend (UP_LOVOL); a coin above its 20-day average closes below its 100h EMA for the first time
while 24h volume is < 0.7x its 30-day norm; long 48h.
Reason: a dip on fading volume is profit taking, not distribution (no seller is forcing it); in calm uptrends dip buyers
and trend funds re-enter at the moving average, and this repeats every leg of a calm trend."""
NAME = "Quiet pullback (UP_LOVOL, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 1.5, "UP_LOVOL"


def signals(g):
    cross = (g.close < g.ema100) & (g.close.shift(1) >= g.ema100.shift(1))
    return cross & (g.close > g.sma480) & (g.vol24 < 0.7 * g.vol24_avg30)
