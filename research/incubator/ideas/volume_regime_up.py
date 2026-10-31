"""Volume regime shift up (discovery 2026-10-19).
Idea: in an uptrend market, a coin whose 30-day dollar volume is >= 2x what it was 30 days earlier, above its 20-day
average and up over 7 days, is bought for 72h (first hour the condition holds).
Reason: a doubling of monthly turnover means a new participant base arrived (new narrative, new venues, funds
starting positions); such inflows are slow-moving capital that keeps buying for weeks, not a one-hour event."""
NAME = "Volume regime up (UP, long 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 72, 2.0, "UP"


def signals(g):
    m = (g.dv30 >= 2 * g.dv30.shift(720)) & (g.close > g.sma480) & (g.ret168 > 0)
    return m & ~m.shift(1, fill_value=False)
