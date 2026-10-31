"""Re-buy after funding settlement (discovery 2026-10-26).
Idea: a coin whose last funding rate is high (> 0.03% and in its own top 10% of 90 days) and above its 50h EMA is
bought at the funding settlement open (00/08/16 UTC) and held 4h. Any market type.
Reason: longs paying high funding close just before settlement to avoid the payment and reopen right after; that
selling-then-buying happens on the same 8-hour clock every day the funding is high."""
NAME = "Funding settle re-buy (ALL, long 4h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 4, 1.0, None


def signals(g):
    h = g.date.dt.hour
    return h.isin([23, 7, 15]) & (g.fund_last > 0.0003) & (g.fund_pct >= 0.9) & (g.close > g.ema50)
