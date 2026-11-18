"""Market-wide short squeeze hour in a bear (discovery 2026-11-16).
Idea: in a falling market (DN), the first hour in which >= 50% of coins rise >= 2% together; buy every coin that rose
>= 2% in that hour and whose last funding is <= 0 (shorts were paying), for 12h (stop 1.5 sigma).
Reason: in a bear the crowd is short; many coins jumping in the same hour is a cross-margin short liquidation cascade
(one engine buying everything at once). Liquidations of shorts trigger more short stops over the next hours, so the
move extends before relief sellers return. Not dip-buying: the entry is after the turn, into forced buying."""
NAME = "Market squeeze hour (DN, long 12h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 12, 1.5, "DN"


def signals(g):
    r1 = g.close / g.close.shift(1) - 1
    up = (r1 >= 0.02).where(r1.notna())
    share = up.groupby(g.date).mean()
    sq = g.date.map(share >= 0.5).fillna(False).astype(bool)
    first = sq & ~sq.shift(1, fill_value=False)
    return first & (r1 >= 0.02) & (g.fund_last <= 0)
