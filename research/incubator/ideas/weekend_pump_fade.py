"""Fade weekend pumps on Monday (discovery 2026-10-07).
Idea: at the close of Sunday 23:00 UTC, coins up >= 2.5 sigma over the weekend (48h) are shorted at Monday 00:00 for 24h.
Reason: weekend books are thin (desks, market makers and arbitrage capital are partly off), so retail-driven moves
overshoot; when weekday liquidity returns, part of the move reverts. Repeats every weekend."""
NAME = "Weekend pump fade (Monday short 24h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = -1, 24, 1.5, None


def signals(g):
    ret48 = g.close / g.close.shift(48) - 1
    sun23 = (g.date.dt.dayofweek == 6) & (g.date.dt.hour == 23)
    return sun23 & (ret48 >= 2.5 * g.sigma)
