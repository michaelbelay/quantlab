"""Trapped longs in a downtrend (discovery 2026-10-12).
Idea: in a downtrend, a coin below its 20-day average and down > 5% over 7 days still has positive funding in its top
10% (90-day percentile); short 48h.
Reason: longs paying high funding on a falling coin are averaging down with leverage; as price keeps falling they
are liquidated (forced sells), and the short collects their funding. Repeats in every bear leg (dip buyers)."""
NAME = "Trapped longs (DN, short 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = -1, 48, 1.5, "DN"


def signals(g):
    m = (g.fund_last > 0) & (g.fund_pct >= 0.9) & (g.close < g.sma480) & (g.ret168 < -0.05)
    return m & ~m.shift(1, fill_value=False)
