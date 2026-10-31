"""US-open fade in a downtrend (discovery 2026-10-26).
Idea: in a falling market (DN), a coin below its 20-day average that rose >= 0.6 sigma between 00:00 and 13:00 UTC
(Asia + Europe hours) is shorted at the 13:00 UTC open for 12h.
Reason: in bear phases the large sellers (funds, ETF outflows, US desks) work in US hours; bounces built on thinner
Asia/Europe books are used as exit liquidity once they arrive, and that schedule repeats every day."""
NAME = "US-open fade (DN, short 12h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = -1, 12, 1.5, "DN"


def signals(g):
    h = g.date.dt.hour
    r13 = g.close / g.close.shift(13) - 1        # bar opening 12:00 closes 13:00; shift(13) = close at 00:00
    return (h == 12) & (r13 >= 0.6 * g.sigma) & (g.close < g.sma480) & (g.ret168 < 0)
