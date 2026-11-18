"""ETH leads a bear-market relief, alts follow (discovery 2026-11-16).
Idea: in a falling market (DN), the first hour ETH beats BTC by >= 3% over 24h with ETH itself up on the day; alts
(not BTC/ETH) below their 20-day average that rose less than ETH over those 24h are bought for 48h (stop 2 sigma).
Reason: in a bear ETH is the most shorted major (the ETH/BTC short is the standard bear trade). ETH outrunning BTC
is that short being squeezed; the covering then rolls down the risk curve into the alts that have not moved yet,
whose shorts cover next. Not dip-buying: it needs the major to turn first; the stop cuts a failed relief."""
NAME = "ETH leads alts in a bear (DN, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 2.0, "DN"


def _series(g, coin):
    s = g.ret24[(g.coin == coin).to_numpy()]
    s.index = g.date[(g.coin == coin).to_numpy()]
    return s


def signals(g):
    eth, btc = _series(g, "ETH"), _series(g, "BTC")
    gap = (eth - btc.reindex(eth.index)).sort_index()
    ev = (gap >= 0.03) & (eth.reindex(gap.index) > 0)
    first = ev & ~ev.shift(1, fill_value=False)
    at = g.date.map(first).fillna(False).astype(bool)
    return at & (g.ret24 < g.date.map(eth)) & (g.close < g.sma480) & ~g.coin.isin(["BTC", "ETH"])
