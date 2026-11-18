"""Asia-session dump rebound in a bear (discovery 2026-11-09).
Idea: in a falling market (DN), a coin that fell >= 4% between 00:00 and 08:00 UTC is bought at 08:00 for 8h
(stop 1 sigma).
Reason: the Asia session is the thinnest part of the day for most alt books, so stop runs and liquidations overshoot;
European and US liquidity arrives after 08:00 and reprices the move. Not plain dip-buying: it trades a liquidity
window, short hold, tight stop."""
NAME = "Asia dump rebound (DN, long 8h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 8, 1.0, "DN"


def signals(g):
    r8 = g.close / g.close.shift(8) - 1
    return (g.date.dt.hour == 7) & (r8 <= -0.04)
