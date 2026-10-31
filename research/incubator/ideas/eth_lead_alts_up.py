"""ETH leads, alts follow (discovery 2026-10-26).
Idea: in an uptrend (UP), the first hour ETH beats BTC by >= 3% over 24h; alts (not BTC/ETH) above their 20-day
average that rose less than ETH over those 24h are bought for 48h.
Reason: ETH outrunning BTC is the first step of risk-on rotation; capital moves down the risk curve (BTC -> ETH ->
large alts -> small alts) over the next days as traders chase the next laggard, which repeats in every alt run."""
NAME = "ETH leads alts (UP, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 2.0, "UP"


def _series(g, coin):
    s = g.ret24[(g.coin == coin).to_numpy()]
    s.index = g.date[(g.coin == coin).to_numpy()]
    return s


def signals(g):
    eth, btc = _series(g, "ETH"), _series(g, "BTC")
    gap = (eth - btc.reindex(eth.index)).sort_index()
    ev = gap >= 0.03
    first = ev & ~ev.shift(1, fill_value=False)
    at = g.date.map(first).fillna(False).astype(bool)
    return at & (g.ret24 < g.date.map(eth)) & (g.close > g.sma480) & ~g.coin.isin(["BTC", "ETH"])
