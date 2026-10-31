"""Volume distribution in a downtrend (discovery 2026-10-07).
Idea: in a falling market, a coin below its 20-day average trades >= 3x its normal 24h volume while its 24h return
stays within +/- 0.5 sigma; short 48h.
Reason: heavy volume without a price rise in a downtrend means a large passive seller (unlocks, funds exiting) is
selling into every bid; when the buyers are used up, price drops. Mirror of absorption_up."""
NAME = "Volume distribution (DN, short 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = -1, 48, 1.5, "DN"


def signals(g):
    m = (g.vol24 >= 3 * g.vol24_avg30) & (g.ret24.abs() <= 0.5 * g.sigma) & (g.close < g.sma480)
    return m & ~m.shift(1, fill_value=False)
