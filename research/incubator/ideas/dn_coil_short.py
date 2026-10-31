"""Tight coil in a downtrend (discovery 2026-10-26).
Idea: in a falling market (DN), a coin below its 20-day average whose 24h high-low range is in its narrowest 10% of
the last 30 days, while funding is still positive (longs paying), is shorted for 48h (first hour per coin).
Reason: a tight range under a falling average is dip buyers holding a level with their stops just below it; positive
funding shows they are long on leverage. In a bear market the level gives way and their forced selling extends it."""
NAME = "Downtrend coil (DN, short 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = -1, 48, 1.5, "DN"


def signals(g):
    rng = g.high.rolling(24).max() / g.low.rolling(24).min() - 1
    pct = rng.rolling(720, min_periods=360).rank(pct=True)
    m = (pct <= 0.10) & (g.close < g.sma480) & (g.fund_last > 0)
    return m & ~m.shift(1, fill_value=False)
