"""Stop sweep of the 20-day low, reclaimed (discovery 2026-10-19).
Idea: in an uptrend market, a 1h candle trades below the coin's previous 20-day low on >= 2x its normal hourly volume
but closes back above that low; long 48h.
Reason: stop-losses cluster just under obvious lows; large players push price there to fill size against the forced
stop sells. If the candle closes back above the level, the selling was only stops, not real supply."""
NAME = "Swept 20d low reclaimed (UP, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 1.5, "UP"


def signals(g):
    hour_avg = g.vol24_avg30 / 24
    return (g.low < g.low480) & (g.close > g.low480) & (g.volume >= 2 * hour_avg)
