"""Market-wide short crowding in an uptrend (discovery 2026-10-19).
Idea: in an uptrend market, when the median funding across all coins is negative and in its bottom 10% of the last
90 days, buy coins above their 20-day average and up over 7 days; long 48h (first hour per coin).
Reason: the whole market leaning short against a rising BTC means many shorts must cover at once on any push up;
they buy the strongest coins first, and longs collect funding meanwhile. Crowding peaks repeat in every cycle."""
NAME = "Market short crowd (UP, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 1.5, "UP"


def signals(g):
    med = g.fund_last.groupby(g.date).median().sort_index()
    pct = med.rolling(90 * 24, min_periods=30 * 24).rank(pct=True)
    crowd = g.date.map((pct <= 0.10) & (med < 0)).fillna(False).astype(bool)
    m = crowd & (g.close > g.sma480) & (g.ret168 > 0)
    return m & ~m.shift(1, fill_value=False)
