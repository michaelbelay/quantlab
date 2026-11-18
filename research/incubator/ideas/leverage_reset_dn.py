"""Leverage reset after a flush (discovery 2026-11-16).
Idea: in a falling market (DN), a coin below its 20-day average whose funding was in its top decile of 90 days two
days ago (longs crowded) and is now <= 0, after a drop of >= 8% over those 48h, is bought for 48h (stop 1.5 sigma).
First hour only.
Reason: the drop was the crowded longs being liquidated; funding at or below zero says they are gone, so the forced
selling that drove the move is finished and the coin trades on real flow again, which in a bear still means a
bounce from the liquidation low. Not dip-buying into a crash: it needs the leverage to have been visibly flushed
(funding from top decile to zero), not just a falling price."""
NAME = "Leverage reset bounce (DN, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 1.5, "DN"


def signals(g):
    r48 = g.close / g.close.shift(48) - 1
    m = (g.fund_pct.shift(48) >= 0.90) & (g.fund_last <= 0) & (r48 <= -0.08) & (g.close < g.sma480)
    return m & ~m.shift(1, fill_value=False)
