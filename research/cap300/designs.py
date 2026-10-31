"""CAP300 strategy designs: few positions, liquid coins, long-only, BTC regime gate.

Each design returns target weights (fraction of equity per coin) decided at the close of each day.
Selection is by liquidity, never by recent return rank (buying the biggest recent movers bought tops
on unseen coins, TG_TOP20_2026-10-04.md).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MIN_AGE, MIN_QVOL = 60, 5e6


def pool(D, coins, k):
    """Point-in-time liquid pool: eligible coins ranked by 30-day mean daily quote volume, top k."""
    c = D["close"][coins]
    liq = D["qvol"][coins].rolling(30, min_periods=20).mean()
    el = (c.notna().cumsum() >= MIN_AGE) & (liq >= MIN_QVOL) & c.notna()
    lr = liq.where(el).rank(axis=1, ascending=False)
    return (lr <= k), lr


def btc_on(D, n=50):
    b = D["close"]["BTC"]
    return (b > b.rolling(n).mean()).astype(float)


def pick(mask: pd.DataFrame, liq_rank: pd.DataFrame, n: int) -> pd.DataFrame:
    """At most n coins from mask, most liquid first."""
    r = liq_rank.where(mask).rank(axis=1, ascending=True)
    return mask & (r <= n)


def weigh(sel: pd.DataFrame, D, coins, mode="ivol", gross=1.0):
    if mode == "ivol":
        v = D["ret"][coins].rolling(30, min_periods=20).std()
        iv = (1 / v).where(sel).fillna(0.0)
        W = iv.div(iv.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    else:
        W = sel.astype(float).div(sel.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    return W * gross


def hold_every(W, every):
    if every <= 1:
        return W
    m = pd.Series(False, index=W.index)
    m.iloc[::every] = True
    return W.where(m, np.nan).ffill().fillna(0.0)


def liquid_trend(D, coins, k=30, n=8, lb=20, every=1, mode="ivol", gross=1.0, **_):
    """Hold up to n of the k most liquid coins whose 20-day return is positive, while BTC > 50-day SMA.
    Mechanism: time-series trend persistence (the TREND_GATED edge that transferred to unseen coins),
    concentrated into liquid coins so positions are large enough for a 300 USDT account."""
    inpool, lr = pool(D, coins, k)
    c = D["close"][coins]
    sel = pick(inpool & (c / c.shift(lb) - 1 > 0), lr, n)
    W = weigh(sel, D, coins, mode, gross).mul(btc_on(D), axis=0)
    return hold_every(W, every)


def _stateful(entry: pd.DataFrame, exit_: pd.DataFrame) -> pd.DataFrame:
    """Position on from an entry day until an exit day (per coin)."""
    e, x = entry.fillna(False).to_numpy(), exit_.fillna(False).to_numpy()
    on = np.zeros_like(e)
    cur = np.zeros(e.shape[1], dtype=bool)
    for t in range(len(e)):
        cur = (cur & ~x[t]) | e[t]
        on[t] = cur
    return pd.DataFrame(on, index=entry.index, columns=entry.columns)


def donchian(D, coins, k=30, n=5, hi=55, lo=20, **_):
    """Turtle breakout: enter on a close above the prior `hi`-day high, exit on a close below the prior
    `lo`-day low; while BTC > 50-day SMA. Mechanism: breakouts from multi-week ranges start trends."""
    inpool, lr = pool(D, coins, k)
    c = D["close"][coins]
    on = _stateful(c > D["high"][coins].rolling(hi).max().shift(1), c < D["low"][coins].rolling(lo).min().shift(1))
    sel = pick(inpool & on, lr, n)
    return weigh(sel, D, coins, "equal").mul(btc_on(D), axis=0)


def pullback(D, coins, k=30, n=5, **_):
    """Buy the dip inside an uptrend: close above its 50-day SMA, 20-day return > 0, and close below its
    5-day SMA (a short pullback); exit when close is back above the 5-day SMA or the trend breaks.
    Mechanism: short-term mean reversion inside a persistent trend."""
    inpool, lr = pool(D, coins, k)
    c = D["close"][coins]
    trend = (c > c.rolling(50).mean()) & (c / c.shift(20) - 1 > 0)
    on = _stateful(trend & (c < c.rolling(5).mean()), (c > c.rolling(5).mean()) | ~trend)
    sel = pick(inpool & on, lr, n)
    return weigh(sel, D, coins, "equal").mul(btc_on(D), axis=0)


def vol_target(W, D, target=0.40, cap=1.5, win=30):
    r = (W.shift(1) * D["ret"].reindex(columns=W.columns).fillna(0)).sum(axis=1)
    rv = r.rolling(win, min_periods=15).std() * np.sqrt(365)
    sc = (target / rv).replace([np.inf, -np.inf], np.nan).fillna(0).clip(upper=cap)
    g = W.abs().sum(axis=1)
    sc = np.minimum(sc, (cap / g).replace([np.inf], np.nan).fillna(0))
    return W.mul(sc, axis=0)


def random_twin(W: pd.DataFrame, D, coins, k, rng: np.random.Generator, every=7) -> pd.DataFrame:
    """Same daily position count, gross exposure and BTC-gate days as W, coins drawn at random from
    the same liquid pool (re-drawn every `every` days). Tests selection skill, not market exposure."""
    inpool, _ = pool(D, coins, k)
    cnt = (W > 0).sum(axis=1).to_numpy()
    gross = W.sum(axis=1).to_numpy()
    P = inpool.reindex(columns=W.columns).fillna(False).to_numpy()
    out = np.zeros(W.shape)
    cur = np.array([], dtype=int)
    for t in range(len(W)):
        avail = np.flatnonzero(P[t])
        if cnt[t] == 0 or len(avail) == 0:
            cur = np.array([], dtype=int)
            continue
        if t % every == 0 or len(cur) != min(cnt[t], len(avail)) or not np.isin(cur, avail).all():
            cur = rng.choice(avail, size=min(cnt[t], len(avail)), replace=False)
        out[t, cur] = gross[t] / len(cur)
    return pd.DataFrame(out, index=W.index, columns=W.columns)


ROUND1 = [
    ("LT-K15-N5", liquid_trend, dict(k=15, n=5)),
    ("LT-K15-N8", liquid_trend, dict(k=15, n=8)),
    ("LT-K30-N5", liquid_trend, dict(k=30, n=5)),
    ("LT-K30-N8", liquid_trend, dict(k=30, n=8)),
    ("LT-K30-N8-weekly", liquid_trend, dict(k=30, n=8, every=7)),
    ("LT-K30-N8-VT40", "vt", dict(k=30, n=8)),
    ("MAJ5-trend", liquid_trend, dict(k=5, n=5)),
    ("DON55-K30-N5", donchian, dict(k=30, n=5, hi=55, lo=20)),
    ("DON20-K30-N5", donchian, dict(k=30, n=5, hi=20, lo=10)),
    ("PB-K30-N5", pullback, dict(k=30, n=5)),
]
