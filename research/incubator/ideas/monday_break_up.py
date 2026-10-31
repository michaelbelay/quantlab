"""Monday break of the weekend range (discovery 2026-10-19).
Idea: in an uptrend market, during Monday (UTC) a coin above its 20-day average closes above its weekend high
(Sat 00:00 - Sun 23:59) for the first time, with 24h volume above its 30-day normal; long 48h.
Reason: weekends are thin, retail-only markets; when weekday desks return and push price through the weekend range,
the move carries real money, and the weekend shorts above the range get stopped. Happens every week."""
NAME = "Monday weekend-range break (UP, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 1.5, "UP"


def signals(g):
    dow, hr = g.date.dt.dayofweek, g.date.dt.hour
    wk_high = g.high.rolling(48).max().where((dow == 6) & (hr == 23))
    wk_high = wk_high.groupby(g.coin).ffill(limit=24)
    m = (dow == 0) & (g.close > wk_high) & (g.close > g.sma480) & (g.vol24 > g.vol24_avg30)
    return m & ~m.shift(1, fill_value=False)
