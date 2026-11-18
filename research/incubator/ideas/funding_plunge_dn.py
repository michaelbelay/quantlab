"""Funding plunges while price holds (discovery 2026-11-16).
Idea: in a falling market (DN), a coin below its 20-day average whose funding fell from the middle of its 90-day
range (percentile >= 0.50 a day ago) to the bottom decile and below zero now, while its 72h return is >= 0, is bought
for 48h (stop 1.5 sigma). First hour only.
Reason: funding collapsing in one day means shorts piled in fast (a crowd chasing a bear narrative), but the price did
not follow: a buyer is absorbing them. The late shorts now pay to hold a position that is not working and cover on
the first move up. Not dip-buying: price must already be flat-to-up over 3 days; the fuel is the fresh short crowd."""
NAME = "Funding plunge, price holds (DN, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 1.5, "DN"


def signals(g):
    r72 = g.close / g.close.shift(72) - 1
    m = (g.fund_pct.shift(24) >= 0.50) & (g.fund_pct <= 0.10) & (g.fund_last < 0) & (r72 >= 0) & (g.close < g.sma480)
    return m & ~m.shift(1, fill_value=False)
