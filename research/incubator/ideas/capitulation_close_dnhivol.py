"""Capitulation day with a reversal close in a wild bear (discovery 2026-11-09).
Idea: on wild downtrend days (DN_HIVOL), at the 23:00 UTC close, a coin down >= 20% over 7 days with 24h volume
>= 2.5x its 30-day average that closes in the top 40% of its 24h range is bought for 72h (stop 2 sigma).
Reason: a week-long slide that ends in a volume climax is margin calls and despair selling; the close far off the
low shows a buyer took all of it. Not plain dip-buying: it needs the climax volume and the intraday reversal, and
the stop cuts a continuation crash."""
NAME = "Capitulation reversal close (DN_HIVOL, long 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 72, 2.0, "DN_HIVOL"


def signals(g):
    hi = g.high.rolling(24).max()
    lo = g.low.rolling(24).min()
    pos = (g.close - lo) / (hi - lo)
    return (g.date.dt.hour == 23) & (g.ret168 <= -0.20) & (g.vol24 >= 2.5 * g.vol24_avg30) & (pos >= 0.6)
