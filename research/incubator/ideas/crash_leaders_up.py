"""Crash leaders (discovery 2026-10-26).
Idea: a market-wide crash starts when >= 50% of coins are down > 8% over 24h. Exactly 72h after the crash start, the
coins in the top 20% of 72h return (fastest recovery) and above their 50h EMA are bought for 72h. Any market type.
Reason: a liquidation crash is forced selling; coins that recover fastest had real spot buyers absorbing it (funds,
treasuries using the dip). Those buyers keep buying and these coins lead the next leg, as after most crashes."""
import pandas as pd

NAME = "Crash leaders (ALL, long 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 72, 2.0, None


def signals(g):
    share = (g.ret24 < -0.08).where(g.ret24.notna()).groupby(g.date).mean().sort_index()
    crash = share >= 0.5
    start = crash & ~crash.shift(1, fill_value=False)
    trig = set(share.index[start.to_numpy()] + pd.Timedelta(hours=72))
    at = g.date.isin(trig)
    r72 = g.close / g.close.shift(72) - 1
    rk = r72.where(at).groupby(g.date).rank(pct=True)
    return at & (rk >= 0.8) & (g.close > g.ema50)
