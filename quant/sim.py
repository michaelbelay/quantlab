"""Market-neutral portfolio simulator on 8h bars (rules: RULES.md "Simulation").

A strategy is a function  scores(panel, t) -> array[N]  evaluated at a rebalance bar t using data
up to bar t-1 only. Higher score = short, lower score = long; NaN = not tradeable. The simulator
picks the k lowest (long) and k highest (short) ELIGIBLE coins, equal notional, both sides the
same count, and holds them until the next rebalance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from .panel import Panel

FEE, SLIP, MMR = 0.0005, 0.0005, 0.01
STOP_SLIP = 0.005           # extra slippage on a stop fill
START_EQUITY = 300.0
MIN_HISTORY = 90            # bars (30 days)
MIN_QVOL_24H = 10e6         # USDT over the last 3 bars


@dataclass
class Result:
    equity: np.ndarray                    # [T] equity at each bar close
    dates: np.ndarray
    trades: int = 0                       # positions opened
    liquidations: int = 0
    stops: int = 0
    liq_loss: float = 0.0                 # USDT lost to liquidations
    fees: float = 0.0
    funding: float = 0.0                  # USDT paid (+) / received (-)
    held: list = field(default_factory=list)   # per rebalance: (t, longs, shorts) coin indices
    leg: np.ndarray | None = None         # [T, 4] per bar: price P&L long, price P&L short, funding long, funding short


def eligible(p: Panel, t: int) -> np.ndarray:
    """Coins tradeable at rebalance bar t (decided on data up to t-1)."""
    if t < 3:
        return np.zeros(p.close.shape[1], bool)
    alive = ~np.isnan(p.close[t - 1])
    hist = (~np.isnan(p.close[max(0, t - MIN_HISTORY):t])).sum(0) >= MIN_HISTORY
    vol = np.nansum(p.qvol[t - 3:t], 0) >= MIN_QVOL_24H
    return alive & hist & vol


def run(p: Panel, scores: Callable[[Panel, int], np.ndarray], k: int, every: int, lev: float = 1.0,
        cost_mult: float = 1.0, start: int = 0, vol_target: float | None = None,
        stop: float | None = None) -> Result:
    """vol_target: if set, gross = equity x min(lev, vol_target / realised vol of own 8h returns over
    30 days) and each position's isolated leverage = max(1, gross / equity). Otherwise gross = lev x equity.
    stop: close a position when price moves this fraction against it from its last (re)entry price; fill at
    the stop price + STOP_SLIP. Any stop, liquidation or delisting forces a full rebalance next bar so both
    sides stay equal in count."""
    T, N = p.close.shape
    c, hi, lo, fund = p.close, p.high, p.low, p.fund
    cost = (FEE + SLIP) * cost_mult
    eq = START_EQUITY
    q = np.zeros(N)                # units held (signed)
    ep = np.zeros(N)               # entry price of the current position
    lp = np.ones(N)                # isolated leverage of the current position
    out = np.full(T, np.nan)
    r = Result(out, p.dates)
    r.leg = np.zeros((T, 4))
    last = None                    # bar of the last rebalance
    force = False                  # a position left the book: rebalance at the next bar
    for t in range(start, T):
        prev = c[t - 1] if t > 0 else c[0]
        # ---------------- rebalance at the open of bar t (= close of t-1)
        if t >= 3 and eq > 0 and (last is None or force or t - last >= every):
            last = t
            force = False
            s = scores(p, t)
            ok = eligible(p, t) & ~np.isnan(s)
            gross_x = lev
            if vol_target is not None:
                hist_eq = out[max(start, t - 91):t]
                hist_eq = hist_eq[~np.isnan(hist_eq)]
                if len(hist_eq) >= 90 and (hist_eq > 0).all():
                    rv = np.std(np.diff(np.log(hist_eq))) * np.sqrt(3 * 365)
                    gross_x = min(lev, vol_target / rv) if rv > 0 else lev
                else:
                    gross_x = 1.0
            pos_lev = max(1.0, gross_x)
            per_leg = eq * gross_x / (2 * k)
            ok &= per_leg >= p.min_notional
            idx = np.where(ok)[0]
            n = min(k, len(idx) // 2)
            tgt = np.zeros(N)
            if n > 0 and hasattr(scores, "pick"):
                longs, shorts = scores.pick(p, t, ok, k, q)    # strategy chooses its own sides (q = current units)
                n = len(longs)
            elif n > 0:
                order = idx[np.argsort(s[idx], kind="stable")]
                longs, shorts = order[:n], order[-n:]
            if n > 0:
                notional = eq * gross_x / (2 * n)
                tgt[longs] = notional / prev[longs]
                tgt[shorts] = -notional / prev[shorts]
                r.held.append((t, longs, shorts))
            else:
                r.held.append((t, np.array([], int), np.array([], int)))
            dq = tgt - q
            px = np.where(np.isnan(prev), 0.0, prev)
            fee = np.abs(dq) @ px * cost
            eq -= fee
            r.fees += fee
            opened = (tgt != 0) & ((q == 0) | (np.sign(q) != np.sign(tgt)))
            r.trades += int(opened.sum())
            changed = dq != 0
            ep = np.where(changed, px, ep)
            lp = np.where(changed, pos_lev, lp)
            q = tgt
        # ---------------- hold through bar t
        held = np.where(q != 0)[0]
        if len(held):
            ci, pi = c[t, held], prev[held]
            dead = np.isnan(ci)                   # delisted / missing: close at last price
            ci = np.where(dead, pi, ci)
            qi, ei, li = q[held], ep[held], lp[held]
            liq_long = (qi > 0) & (lo[t, held] <= ei * (1 - 1 / li + MMR))
            liq_short = (qi < 0) & (hi[t, held] >= ei * (1 + 1 / li - MMR))
            liq = (liq_long | liq_short) & ~dead
            pnl = qi * (ci - pi)
            if liq.any():
                # the position's remaining margin is lost: loss from entry = margin
                margin = np.abs(qi[liq]) * ei[liq] / li[liq]
                already = qi[liq] * (pi[liq] - ei[liq])       # P&L booked on earlier bars
                pnl[liq] = -margin - already
                r.liquidations += int(liq.sum())
                r.liq_loss += float(margin.sum())
            stp = np.zeros(len(held), bool)
            if stop is not None:
                s_long = (qi > 0) & (lo[t, held] <= ei * (1 - stop))
                s_short = (qi < 0) & (hi[t, held] >= ei * (1 + stop))
                stp = (s_long | s_short) & ~liq & ~dead
                if stp.any():
                    sp = np.where(qi > 0, ei * (1 - stop) * (1 - STOP_SLIP), ei * (1 + stop) * (1 + STOP_SLIP))
                    # a bar that opens beyond the stop fills at the open (= previous close)
                    sp = np.where(qi > 0, np.minimum(sp, pi), np.maximum(sp, pi))
                    pnl[stp] = qi[stp] * (sp[stp] - pi[stp])
                    fee = float(np.abs(qi[stp]) @ sp[stp] * cost)
                    eq -= fee
                    r.fees += fee
                    r.stops += int(stp.sum())
            f = np.where(liq | dead | stp, 0.0, qi * ci * fund[t, held])
            lg = qi > 0
            r.leg[t] = (pnl[lg].sum(), pnl[~lg].sum(), -f[lg].sum(), -f[~lg].sum())
            eq += pnl.sum() - f.sum()
            r.funding += float(f.sum())
            gone = held[liq | dead | stp]
            q[gone] = 0.0
            if len(gone) and stop is not None:
                force = True
        out[t] = eq
        if eq <= 0:
            out[t:] = 0.0
            break
    return r
