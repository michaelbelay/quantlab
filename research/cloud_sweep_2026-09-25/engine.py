"""Vectorised daily portfolio backtester for weight-based strategies.

Timing: weights decided with data up to the close of day t-1 are held over day t.
Daily bar t covers 00:00 -> 24:00 UTC (close = 23:00 1h bar close).
Costs: |delta weight| * cost_per_side at each rebalance.
Funding: events at 08:00, 16:00 of day t and 00:00 of day t+1 are charged to the
position held over day t (event at 00:00 of t+1 belongs to the day that ends there).
"""
from __future__ import annotations
import json
import numpy as np
import pandas as pd

PANEL = '/home/claude/research/panel/'
SPLIT = '/mnt/user-data/uploads/quantlab/data/market/universe/split_140.json'
COST = 0.0010   # fee 0.05% + slippage 0.05% per side


def load_daily():
    c = pd.read_parquet(PANEL + 'close_1h.parquet')
    h = pd.read_parquet(PANEL + 'high_1h.parquet')
    l = pd.read_parquet(PANEL + 'low_1h.parquet')
    v = pd.read_parquet(PANEL + 'qvol_1h.parquet')
    f = pd.read_parquet(PANEL + 'funding_1h.parquet')
    D = {}
    D['close'] = c.resample('1D').last()
    D['high'] = h.resample('1D').max()
    D['low'] = l.resample('1D').min()
    D['qvol'] = v.resample('1D').sum(min_count=1)
    D['funding'] = f.shift(-1).resample('1D').sum().reindex(D['close'].index).fillna(0.0)
    # a coin's first/last partial day is dropped by requiring a full day of closes
    n = c.notna().resample('1D').sum()
    D['close'] = D['close'].where(n >= 20)
    D['ret'] = D['close'].pct_change(fill_method=None)
    return D


def split():
    s = json.load(open(SPLIT))
    return s['dev'], s['holdout']


def run(W: pd.DataFrame, D: dict, cost=COST, fund_mult=1.0):
    """W: target weights decided at end of day t (index t). Returns dict of series."""
    W = W.reindex(columns=D['ret'].columns).fillna(0.0)
    held = W.shift(1).fillna(0.0)                     # held over day t
    ret = D['ret'].fillna(0.0)
    fund = D['funding'] * fund_mult
    gross_pnl = held * ret
    fund_pnl = -held * fund                           # long pays positive funding
    # rebalance at end of day t-1 from drifted weights to target
    drift = held.shift(1).fillna(0.0) * (1 + ret.shift(1).fillna(0.0))
    turnover = (held - drift).abs()
    cost_pnl = -turnover * cost
    pnl = gross_pnl + fund_pnl + cost_pnl             # per coin per day, in equity fraction
    port = pnl.sum(axis=1)
    return dict(pnl=pnl, port=port, held=held, turnover=turnover.sum(axis=1),
                cost=cost_pnl.sum(axis=1), fund=fund_pnl.sum(axis=1))


def trades_pf(pnl: pd.DataFrame, held: pd.DataFrame):
    """Trade = contiguous run of same-sign position in one coin. Returns (pf, n, win_rate, list)."""
    out = []
    sgn = np.sign(held.values)
    P = pnl.values
    for j in range(sgn.shape[1]):
        s = sgn[:, j]
        cur, acc = 0, 0.0
        for i in range(len(s)):
            if s[i] != cur:
                if cur != 0:
                    out.append(acc)
                cur, acc = s[i], 0.0
            if cur != 0:
                acc += P[i, j]
            elif P[i, j] != 0:                      # exit-cost day after flat
                if out:
                    out[-1] += P[i, j]
        if cur != 0:
            out.append(acc)
    a = np.array(out)
    if len(a) == 0:
        return dict(pf=np.nan, n=0, win=np.nan)
    gp, gl = a[a > 0].sum(), -a[a < 0].sum()
    return dict(pf=gp / gl if gl > 0 else np.inf, n=len(a), win=(a > 0).mean())


def stats(port: pd.Series, start=None, end=None):
    p = port.loc[start:end]
    p = p[p.index >= p.ne(0).idxmax()] if p.ne(0).any() else p
    eq = (1 + p).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    yrs = len(p) / 365.25
    tot = eq.iloc[-1] - 1 if len(eq) else 0.0
    cagr = eq.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 and eq.iloc[-1] > 0 else -1
    sh = p.mean() / p.std() * np.sqrt(365) if p.std() > 0 else 0
    dpf = p[p > 0].sum() / -p[p < 0].sum() if (p < 0).any() else np.inf
    return dict(total=tot, cagr=cagr, maxdd=dd, sharpe=sh, daily_pf=dpf, days=len(p))


REGIMES = {'2021': ('2021-01-01', '2021-12-31'), '2022': ('2022-01-01', '2022-12-31'),
           '2023_24': ('2023-01-01', '2024-12-31'), '2025_26': ('2025-01-01', '2026-12-31')}


def full_report(W, D, label=''):
    r = run(W, D)
    r2c = run(W, D, cost=2 * COST)
    r2f = run(W, D, fund_mult=2.0)
    t = trades_pf(r['pnl'], r['held'])
    t2c = trades_pf(r2c['pnl'], r2c['held'])
    t2f = trades_pf(r2f['pnl'], r2f['held'])
    s = stats(r['port'])
    rep = dict(label=label, pf=t['pf'], trades=t['n'], win=t['win'], pf_2xcost=t2c['pf'],
               pf_2xfund=t2f['pf'], **s,
               turnover_yr=r['turnover'].sum() / max(s['days'], 1) * 365,
               cost_yr=r['cost'].sum() / max(s['days'], 1) * 365,
               fund_yr=r['fund'].sum() / max(s['days'], 1) * 365)
    for k, (a, b) in REGIMES.items():
        rep['reg_' + k] = (1 + r['port'].loc[a:b]).prod() - 1
    return rep, r
