"""Smooth trend in a calm bull (discovery 2026-10-19).
Idea: on calm uptrend days (UP_LOVOL), a coin up > 10% over 7 days whose path was smooth (efficiency ratio: 7-day net
move / sum of absolute hourly moves >= 0.25) and above its 20-day average is bought for 72h.
Reason: a smooth climb comes from a patient, steady buyer (fund or treasury working a large order over days), not from
a retail spike; such orders take weeks to fill, so the buying continues after the signal."""
NAME = "Smooth trend (UP_LOVOL, long 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 72, 2.0, "UP_LOVOL"


def signals(g):
    path = g.close.diff().abs().rolling(168).sum()
    er = (g.close - g.close.shift(168)).abs() / path
    m = (g.ret168 > 0.10) & (er >= 0.25) & (g.close > g.sma480)
    return m & ~m.shift(1, fill_value=False)
