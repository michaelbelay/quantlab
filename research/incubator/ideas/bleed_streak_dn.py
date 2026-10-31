"""Slow bleed streak in a calm downtrend (discovery 2026-10-26).
Idea: on calm downtrend days (DN_LOVOL), a coin that closed lower on at least 6 of the last 7 days (24h steps at
00:00 UTC) and lost 5-25% over 7 days (slow, not a crash) is shorted for 48h.
Reason: a steady daily decline is a scheduled seller (token emissions, unlock recipients, treasury sales) selling a
fixed amount each day; in a calm bear market dip buyers are scarce, so the schedule keeps pushing price down."""
NAME = "Bleed streak (DN_LOVOL, short 48h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = -1, 48, 1.5, "DN_LOVOL"


def signals(g):
    down = sum((g.ret24.shift(24 * i) < 0).astype(int) for i in range(7))
    return (g.date.dt.hour == 23) & (down >= 6) & (g.ret168 <= -0.05) & (g.ret168 >= -0.25)
