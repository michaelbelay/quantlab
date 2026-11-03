"""Quiet breakdown in a calm bear (discovery 2026-11-02).
Idea: on calm downtrend days (DN_LOVOL), a coin closing below its 20-day low for the first time while its 24h volume is
below its 30-day mean is shorted for 72h.
Reason: a breakdown on low volume is not a capitulation (no forced sellers flushed out, no buyers stepping in); holders
leave slowly as the level fails, and with no climax to absorb supply the bleed continues for days."""
NAME = "Quiet breakdown (DN_LOVOL, short 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = -1, 72, 1.5, "DN_LOVOL"


def signals(g):
    return (g.close < g.low480) & (g.close.shift(1) >= g.low480.shift(1)) & (g.vol24 < g.vol24_avg30)
