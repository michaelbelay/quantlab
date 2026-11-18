"""Market-wide liquidation hour in a bear (discovery 2026-11-09).
Idea: in a falling market (DN), the first hour in which >= 50% of coins drop >= 2% together; buy every coin that
dropped >= 2% in that hour, for 24h (stop 1.5 sigma).
Reason: many coins falling hard in the same hour is a cross-margin liquidation cascade (one engine selling everything
at once), not coin news; the forced flow ends within the hour and arbitrage/market makers pull prices back. Not
dip-buying a slow crash: it needs a one-hour synchronized flush, and the stop handles a second wave."""
NAME = "Market flush hour (DN, long 24h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 24, 1.5, "DN"


def signals(g):
    r1 = g.close / g.close.shift(1) - 1
    down = (r1 <= -0.02).where(r1.notna())
    share = down.groupby(g.date).mean()
    flush = g.date.map(share >= 0.5).fillna(False).astype(bool)
    first = flush & ~flush.shift(1, fill_value=False)
    return first & (r1 <= -0.02)
