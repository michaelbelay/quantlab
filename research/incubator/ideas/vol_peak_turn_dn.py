"""Volatility peak then turn (discovery 2026-11-16).
Idea: in a falling market (DN), the first hour a coin's 20-day volatility (sigma) reaches its highest level of the
last 90 days while the coin is down >= 15% over 7 days and has closed back above its EMA50, is bought for 72h
(stop 2 sigma).
Reason: volatility peaks when the liquidation cascade is widest (margin calls across all leverage tiers); once
everyone who could be liquidated has been, open interest is reset and there is nobody left to force-sell. The
close above EMA50 shows the first buyers are already in. Not plain dip-buying: it needs the vol climax and a
reclaimed average, and a 2-sigma stop in a high-sigma coin is wide but bounded."""
NAME = "Vol peak then turn (DN, long 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 72, 2.0, "DN"


def signals(g):
    peak = g.sigma >= g.sigma.rolling(90 * 24, min_periods=30 * 24).max()
    m = peak & (g.ret168 <= -0.15) & (g.close > g.ema50)
    return m & ~m.shift(1, fill_value=False)
