"""Weight generators. Every signal uses only data up to and including day t (the decision day)."""
from __future__ import annotations
import numpy as np
import pandas as pd

MIN_AGE = 60          # days listed before a coin is eligible
MIN_QVOL = 5e6        # 30d mean daily quote volume, USD


def eligible(D, coins):
    c = D['close'][coins]
    age = c.notna().cumsum()
    liq = D['qvol'][coins].rolling(30, min_periods=20).mean()
    return (age >= MIN_AGE) & (liq >= MIN_QVOL) & c.notna()


def _rebal_mask(index, every):
    m = pd.Series(False, index=index)
    m.iloc[::every] = True
    return m


def _hold_between(W, every):
    """Keep weights constant between rebalance days (targets only change on rebalance days)."""
    mask = _rebal_mask(W.index, every)
    W2 = W.where(mask, np.nan).ffill().fillna(0.0)
    return W2


def xs_rank_ls(score: pd.DataFrame, elig: pd.DataFrame, n: int, every: int,
               long_only=False, invvol=None, gross=1.0):
    """Long top-n / short bottom-n by score. Gross exposure = gross (split evenly per side)."""
    s = score.where(elig)
    cnt = s.notna().sum(axis=1)
    rk_hi = s.rank(axis=1, ascending=False)
    rk_lo = s.rank(axis=1, ascending=True)
    ok = cnt >= 2 * n + 4
    L = (rk_hi <= n) & ok.values[:, None]
    S = (rk_lo <= n) & ok.values[:, None]
    if invvol is not None:
        iv = (1 / invvol).where(elig)
        wl = iv.where(L, 0).fillna(0); wl = wl.div(wl.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
        ws = iv.where(S, 0).fillna(0); ws = ws.div(ws.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    else:
        wl = L.astype(float).div(L.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
        ws = S.astype(float).div(S.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    if long_only:
        W = wl * gross
    else:
        W = (wl - ws) * (gross / 2)
    return _hold_between(W, every)


def vol(D, coins, n=30):
    return D['ret'][coins].rolling(n, min_periods=20).std()


# ---------------------------------------------------------------- families
def xs_mom(D, coins, lb=30, skip=1, n=5, every=7, long_only=False, ivol=False, btc_filter=False):
    c = D['close'][coins]
    score = c.shift(skip) / c.shift(lb) - 1
    el = eligible(D, coins)
    W = xs_rank_ls(score, el, n, every, long_only=long_only,
                   invvol=vol(D, coins) if ivol else None)
    if btc_filter:
        b = D['close']['BTC']
        on = (b > b.rolling(100).mean())
        W = W.mul(on.astype(float), axis=0)
    return W


def carry(D, coins, lb=7, n=5, every=7, ivol=False):
    f = D['funding'][coins].rolling(lb, min_periods=max(2, lb // 2)).mean()
    score = -f                      # low funding -> long, high funding -> short
    el = eligible(D, coins) & D['funding'][coins].rolling(lb).count().ge(lb // 2)
    return xs_rank_ls(score, el, n, every, invvol=vol(D, coins) if ivol else None)


def xs_rev(D, coins, lb=3, n=5, every=1):
    c = D['close'][coins]
    score = -(c / c.shift(lb) - 1)
    return xs_rank_ls(score, eligible(D, coins), n, every)


def ts_trend(D, coins, lb=50, target_vol=0.20, long_only=False, every=1, max_gross=1.0,
             method='ret'):
    c = D['close'][coins]
    if method == 'ret':
        sig = np.sign(c / c.shift(lb) - 1)
    else:  # ema cross fast=lb/4 slow=lb
        sig = np.sign(c.ewm(span=max(2, lb // 4)).mean() - c.ewm(span=lb).mean())
    if long_only:
        sig = sig.clip(lower=0)
    el = eligible(D, coins)
    sig = sig.where(el, 0).fillna(0)
    v = vol(D, coins) * np.sqrt(365)
    n_el = el.sum(axis=1).replace(0, np.nan)
    # equal risk: each coin targets target_vol / n_el of portfolio vol (ignores correlation)
    w = sig * (target_vol / v).div(n_el, axis=0)
    w = w.fillna(0)
    g = w.abs().sum(axis=1)
    scale = (max_gross / g).clip(upper=1).fillna(0)
    W = w.mul(scale, axis=0)
    return _hold_between(W, every)


def btc_gate(D, n=100):
    b = D['close']['BTC']
    return (b > b.rolling(n).mean()).astype(float)


def trend_gated(D, coins, lb=20, n_sma=100, every=1, target_vol=0.3, method='ema'):
    W = ts_trend(D, coins, lb=lb, target_vol=target_vol, long_only=True, every=every, method=method)
    return W.mul(btc_gate(D, n_sma), axis=0)


def dual_mom(D, coins, lb=30, n=5, every=7, n_sma=100):
    c = D['close'][coins]
    score = c.shift(1) / c.shift(lb) - 1
    el = eligible(D, coins) & (score > 0)
    s = score.where(el)
    rk = s.rank(axis=1, ascending=False)
    L = (rk <= n)
    W = L.astype(float) / n            # unfilled slots stay in cash
    W = _hold_between(W, every)
    return W.mul(btc_gate(D, n_sma), axis=0)
