"""US session long in an uptrend (discovery 2026-10-26).
Idea: in an uptrend (UP), a coin above its 20-day average, up over 24h and up > 5% over 7 days is bought at the
13:00 UTC open and held 8h (the US session).
Reason: in bull phases US institutions (ETF creations, funds) buy during their own trading hours; that flow arrives on
a fixed clock every weekday and lifts the strongest coins most, while Asia/Europe hours carry less of it."""
NAME = "US session long (UP, long 8h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 8, 1.5, "UP"


def signals(g):
    return (g.date.dt.hour == 12) & (g.close > g.sma480) & (g.ret24 > 0) & (g.ret168 > 0.05)
