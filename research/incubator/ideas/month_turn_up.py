"""Turn of the month in an uptrend (discovery 2026-10-26).
Idea: in an uptrend (UP), every coin above its 20-day average is bought at 00:00 UTC on the 1st of the month, 72h.
Reason: monthly money arrives on a calendar, not on a signal (salaries -> DCA plans, fund subscriptions, treasury
buy programs); in a bull phase that new cash is put to work in the first days of the month, every month."""
import pandas as pd

NAME = "Month turn (UP, long 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 72, 2.0, "UP"


def signals(g):
    nxt = g.date + pd.Timedelta(hours=1)          # entry bar = first hour of the new month
    return (nxt.dt.day == 1) & (nxt.dt.hour == 0) & (g.close > g.sma480)
