"""Crowded shorts at the bottom of a bear (discovery 2026-11-09).
Idea: in a falling market (DN), a coin below its 20-day average whose funding is negative and in its lowest 5% of the
last 90 days, at the first hour its 24h return turns positive, is bought for 48h (stop 1.5 sigma).
Reason: late shorts pile in after the move and pay funding to hold; once price stops falling they are paying to lose,
and their forced covering (stops, liquidations) lifts the coin. Not plain dip-buying: the trigger needs the turn up
and the short crowd as the fuel; the stop cuts a real crash."""
NAME = "Crowded shorts bottom (DN, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 1.5, "DN"


def signals(g):
    m = (g.fund_last < 0) & (g.fund_pct <= 0.05) & (g.close < g.sma480) & (g.ret24 > 0)
    return m & ~m.shift(1, fill_value=False)
