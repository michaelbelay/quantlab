"""Market-wide funding euphoria (discovery 2026-10-12).
Idea: when the median funding across all coins is in its top 5% of the last 90 days, short coins whose own funding is
in their top 5% and that rose > 20% over 7 days; short 48h. Any market type.
Reason: when the whole market is levered long at once, a small dip triggers long liquidations everywhere, and the
most-levered, most-extended coins fall hardest; the short also collects the high funding. Repeats at every euphoric top."""
NAME = "Funding euphoria (all markets, short 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = -1, 48, 2.0, None


def signals(g):
    med = g.fund_last.groupby(g.date).median().sort_index()
    pct = med.rolling(90 * 24, min_periods=30 * 24).rank(pct=True)
    euph = g.date.map(pct >= 0.95).fillna(False).astype(bool)
    m = euph & (g.fund_pct >= 0.95) & (g.ret168 > 0.2)
    return m & ~m.shift(1, fill_value=False)
