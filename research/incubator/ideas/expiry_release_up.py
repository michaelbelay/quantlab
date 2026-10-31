"""Monthly options expiry release in an uptrend (discovery 2026-10-26).
Idea: in an uptrend (UP), right after the monthly Deribit options expiry (last Friday of the month, 08:00 UTC), coins
above their 20-day average are bought at the 09:00 UTC open for 72h.
Reason: before a big expiry, option dealers' hedging pins prices near large strikes; once the options expire the hedges
are unwound and the pin is gone, so the prevailing trend resumes. Expiry is on a fixed calendar every month."""
NAME = "Expiry release (UP, long 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 72, 2.0, "UP"


def signals(g):
    d = g.date
    last_friday = (d.dt.weekday == 4) & (d.dt.day + 7 > d.dt.days_in_month)
    return last_friday & (d.dt.hour == 8) & (g.close > g.sma480)
