"""Quiet after the dump (discovery 2026-10-19).
Idea: in a falling market, a coin fell >= 3 sigma in the 72h that ended 24h ago; over the last 24h it held flat
(|24h return| <= 0.5 sigma) on below-normal volume (24h volume <= 0.8x its 30-day normal); long 48h.
Reason: after a dump, forced sellers (liquidations, stop-outs) are done; when price then holds on fading volume, no
new seller is coming and short sellers who arrived late start covering. Every sell-off has this exhaustion phase."""
NAME = "Quiet after dump (DN, long 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 48, 1.5, "DN"


def signals(g):
    drop = g.close.shift(24) / g.close.shift(96) - 1
    m = (drop <= -3 * g.sigma) & (g.ret24.abs() <= 0.5 * g.sigma) & (g.vol24 <= 0.8 * g.vol24_avg30)
    return m & ~m.shift(1, fill_value=False)
