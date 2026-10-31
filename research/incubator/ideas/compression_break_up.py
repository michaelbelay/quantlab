"""Volatility compression, then expansion (discovery 2026-10-07).
Idea: in an uptrend, a coin whose previous 24h range is < half its 30-day average 24h range closes above that 24h high
on >= 2x normal hourly volume; long 24h.
Reason: a tight range collects stops and resting orders on both sides; when it breaks with volume, the stops of the
short sellers and breakout buyers push price further, and the trend backdrop makes the up side the likelier one."""
NAME = "Compression breakout (UP, long 24h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 24, 1.0, "UP"


def signals(g):
    hi24 = g.high.shift(1).rolling(24).max()
    lo24 = g.low.shift(1).rolling(24).min()
    rng = hi24 / lo24 - 1
    tight = rng < 0.5 * rng.rolling(720).mean()
    vol_x = g.volume / (g.vol24_avg30 / 24)
    m = tight & (g.close > hi24) & (vol_x >= 2)
    return m & ~m.shift(1, fill_value=False)
