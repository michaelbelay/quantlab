"""Volume absorption in an uptrend (discovery 2026-10-07).
Idea: in an uptrend, a coin above its 20-day average trades >= 3x its normal 24h volume while its 24h return stays
within +/- 0.5 sigma; long 48h.
Reason: very heavy volume that does not move price means a large passive buyer is absorbing all the selling
(accumulation); once the sellers are exhausted, price moves up. Large holders accumulate this way in every trend."""
NAME = "Volume absorption (UP, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 1.5, "UP"


def signals(g):
    m = (g.vol24 >= 3 * g.vol24_avg30) & (g.ret24.abs() <= 0.5 * g.sigma) & (g.close > g.sma480)
    return m & ~m.shift(1, fill_value=False)
