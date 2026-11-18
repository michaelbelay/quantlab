"""Whole market short in a bear (discovery 2026-11-09).
Idea: in a falling market (DN), when the median last funding rate across all coins is below zero (the whole market
pays to be short), buy each coin whose own funding is negative, at the first hour of that state, for 48h (stop 2 sigma).
Reason: a market-wide short crowd in a bear is late, levered and paying carry; any lift triggers stops across many
coins at once and the covering feeds itself. Not dip-buying: the trigger is crowd positioning, not a price drop."""
NAME = "Market short crowd (DN, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 2.0, "DN"


def signals(g):
    med = g.fund_last.groupby(g.date).median()
    crowd = g.date.map(med < 0).fillna(False).astype(bool)
    m = crowd & (g.fund_last < 0)
    return m & ~m.shift(1, fill_value=False)
