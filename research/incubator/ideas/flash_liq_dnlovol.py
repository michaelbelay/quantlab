"""Flash liquidation candle in a calm bear (discovery 2026-11-09).
Idea: on calm downtrend days (DN_LOVOL), a 1h candle that falls >= 3% and >= 3x the coin's hourly sigma, on volume
>= 5x its average hour of the last day, but closes in the upper half of its range, is bought for 12h (stop 1 sigma).
Reason: a single-hour cascade in a quiet market is forced selling (long liquidations, stop runs), not news; the close
off the low shows the forced flow was absorbed, and the price drifts back once it is gone. Calm days only, so it is
not buying into a real crash; the stop cuts a second leg."""
import numpy as np

NAME = "Flash liquidation wick (DN_LOVOL, long 12h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 12, 1.0, "DN_LOVOL"


def signals(g):
    r1 = g.close / g.close.shift(1) - 1
    big = (r1 <= -0.03) & (r1 <= -3 * g.sigma / np.sqrt(24))
    vol = g.volume >= 5 * g.vol24.shift(1) / 24
    upper = (g.close - g.low) >= 0.5 * (g.high - g.low)
    return big & vol & upper
