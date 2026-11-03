"""Market-wide calm, buy the leaders (discovery 2026-11-02).
Idea: in an uptrend (UP), the first hour in which the median coin's 24h high-low range is in its narrowest 10% of the
last 30 days; buy every coin in the top 20% by 7-day return that is above its 20-day average, hold 72h.
Reason: when the whole market goes quiet, leverage and option sellers pile in for carry; the expansion that follows in
an uptrend breaks upward first in the coins that already have buyers, and the shorts selling volatility must chase."""
NAME = "Market calm leaders (UP, long 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 72, 2.0, "UP"


def signals(g):
    rng = g.high.rolling(24).max() / g.low.rolling(24).min() - 1
    med = rng.groupby(g.date).median().sort_index()
    calm = med.rolling(720, min_periods=360).rank(pct=True) <= 0.10
    first = calm & ~calm.shift(1, fill_value=False)
    lead = g.ret168.groupby(g.date).rank(pct=True) >= 0.8
    return g.date.map(first).fillna(False).astype(bool) & lead & (g.close > g.sma480)
