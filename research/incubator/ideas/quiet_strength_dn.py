"""Quiet strength in a bear (discovery 2026-11-16).
Idea: in a falling market (DN), a coin above a rising EMA100 whose 24h high-low range is in its narrowest 10% of the
last 30 days, while funding is <= 0 (shorts paying or nobody levered long), is bought for 48h (stop 1.5 sigma).
Reason: a coin that holds above a rising average while the market falls has a buyer who keeps lifting offers; the
tight range means sellers are exhausted and the bear-market shorts on it are paying to be wrong. When the range
resolves, their covering is the fuel. Not dip-buying: price is above its average, not in a crash; the stop sits
just under the coil."""
NAME = "Quiet strength (DN, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 1.5, "DN"


def signals(g):
    rng = g.high.rolling(24).max() / g.low.rolling(24).min() - 1
    pct = rng.rolling(720, min_periods=360).rank(pct=True)
    m = (pct <= 0.10) & (g.close > g.ema100) & (g.ema100 > g.ema100.shift(24)) & (g.fund_last <= 0)
    return m & ~m.shift(1, fill_value=False)
