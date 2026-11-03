"""Leaders through a bull-market washout (discovery 2026-11-02).
Idea: in an uptrend (UP), on days when >= 70% of coins are below their 20-day average (checked at 00:00 UTC), buy the
coins that are still above it, hold 72h.
Reason: a broad dip inside a BTC uptrend is forced deleveraging hitting everything; coins that held their trend through
it have a committed buyer, and they lead when the market's selling pressure ends."""
NAME = "Washout leaders (UP, long 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 72, 2.0, "UP"


def signals(g):
    below = (g.close < g.sma480).where(g.sma480.notna())
    share = below.groupby(g.date).mean()
    wash = g.date.map(share >= 0.7).fillna(False).astype(bool)
    return wash & (g.date.dt.hour == 0) & (g.close > g.sma480)
