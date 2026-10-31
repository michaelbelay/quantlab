"""Attention fade in a downtrend (discovery 2026-10-19).
Idea: in a falling market, a coin whose 30-day dollar volume is <= half of what it was 30 days earlier, below its
20-day average and down over 7 days, is shorted for 72h (first hour the condition holds).
Reason: halving turnover means buyers have left the coin; market makers thin their books and the remaining holders
sell into an empty bid. Coins that lose attention in a bear market bleed slowly, and this repeats coin after coin."""
NAME = "Attention fade (DN, short 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = -1, 72, 2.0, "DN"


def signals(g):
    m = (g.dv30 <= 0.5 * g.dv30.shift(720)) & (g.close < g.sma480) & (g.ret168 < 0)
    return m & ~m.shift(1, fill_value=False)
