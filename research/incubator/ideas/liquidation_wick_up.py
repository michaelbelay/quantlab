"""Liquidation wick bought back (discovery 2026-10-12).
Idea: in an uptrend, a coin above its 20-day average prints a 1h candle whose lower wick is >= 0.6 sigma (of 24h
moves), closes in the top 30% of the candle's range, on >= 4x normal hourly volume; long 24h.
Reason: a long-liquidation cascade swept the stops and was absorbed within the hour; the forced sellers are gone and
the buyers who caught the wick defend it. Repeats because leverage builds up in every uptrend."""
NAME = "Liquidation wick (UP, long 24h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 24, 1.5, "UP"


def signals(g):
    body_lo = g[["open", "close"]].min(axis=1)
    wick = (body_lo - g.low) / g.open
    strong_close = g.close >= g.low + 0.7 * (g.high - g.low)
    m = (wick >= 0.6 * g.sigma) & strong_close & (g.volume >= 4 * g.vol24_avg30 / 24) & (g.close > g.sma480)
    return m
