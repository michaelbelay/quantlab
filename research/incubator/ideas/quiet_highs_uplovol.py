"""Quiet at the highs in calm uptrends (discovery 2026-10-12).
Idea: on calm uptrend days (UP_LOVOL), a coin within 3% of its 20-day high, up over 7 days, with 24h volume at most
half of its 30-day normal; long 72h.
Reason: price holding at the highs while volume dries up means nobody is selling there (supply exhausted); the next
buyers lift it with little resistance. Repeats in every calm bull phase."""
NAME = "Quiet at highs (UP_LOVOL, long 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 72, 2.0, "UP_LOVOL"


def signals(g):
    near_high = g.close >= 0.97 * g.high.rolling(480).max()
    m = near_high & (g.vol24 <= 0.5 * g.vol24_avg30) & (g.ret168 > 0)
    return m & ~m.shift(1, fill_value=False)
