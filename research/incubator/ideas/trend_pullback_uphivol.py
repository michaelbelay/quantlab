"""EMA pullback in a hot bull (discovery 2026-11-02).
Idea: on wild uptrend days (UP_HIVOL), a coin in a stacked trend (EMA50 > EMA100, above its 20-day average, up over 7
days) whose hourly low touches the EMA100 while the bar closes above it is bought for 48h (first hour per coin).
Reason: in fast bull markets trend funds and systematic dip buyers keep resting bids at the medium-term average; a
touch that holds shows those bids are still there, and the trend resumes once the short-term longs are shaken out."""
NAME = "EMA100 pullback (UP_HIVOL, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 1.5, "UP_HIVOL"


def signals(g):
    m = (g.ema50 > g.ema100) & (g.close > g.sma480) & (g.ret168 > 0) & (g.low <= g.ema100) & (g.close > g.ema100)
    return m & ~m.shift(1, fill_value=False)
