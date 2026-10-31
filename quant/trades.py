"""Per-coin trade simulation for Protocol C (rules: PROTOCOL_C.md "Execution model").

A family gives, per coin, boolean arrays `long_sig` / `short_sig` (decided on the bar CLOSE) and the exit
geometry. Entry is at the NEXT bar's open; one position per coin at a time.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

FEE, SLIP, STOP_EXTRA = 0.0005, 0.0005, 0.0005
MIN_LISTED_DAYS, MIN_QVOL_24H = 30, 10e6


@dataclass
class Exit:
    stop_atr: float = 2.0
    tp_atr: float | None = 4.0
    max_hold: int = 48                 # bars
    opposite: bool = False             # exit when the opposite signal fires


def atr(df: pd.DataFrame, n: int = 14) -> np.ndarray:
    h, l, c = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def eligible(df: pd.DataFrame, bars_per_day: int) -> np.ndarray:
    qv24 = df["qvol"].rolling(bars_per_day, min_periods=bars_per_day).sum().to_numpy()
    listed = np.arange(len(df)) >= MIN_LISTED_DAYS * bars_per_day
    return listed & (qv24 >= MIN_QVOL_24H)


def simulate(df: pd.DataFrame, long_sig: np.ndarray, short_sig: np.ndarray, ex: Exit, a: np.ndarray,
             bars_per_day: int, cost_mult: float = 1.0) -> list[dict]:
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    fund = df["fund"].to_numpy()
    dates = df["date"].to_numpy()
    ok = eligible(df, bars_per_day)
    n = len(df)
    cost = (FEE + SLIP) * cost_mult
    out = []
    i = 0
    sig_idx = np.where((long_sig | short_sig) & ok & ~np.isnan(a))[0]
    for s in sig_idx:
        if s < i or s + 1 >= n:
            continue
        side = 1 if long_sig[s] else -1
        if long_sig[s] and short_sig[s]:
            continue
        e = s + 1
        px = o[e]
        if not np.isfinite(px) or px <= 0:
            continue
        stop = px - side * ex.stop_atr * a[s]
        tp = px + side * ex.tp_atr * a[s] if ex.tp_atr else None
        end = min(n - 1, e + ex.max_hold - 1)
        hh, ll, oo = h[e:end + 1], l[e:end + 1], o[e:end + 1]
        if side == 1:
            hit_stop = ll <= stop
            hit_tp = hh >= tp if tp is not None else np.zeros_like(hit_stop)
        else:
            hit_stop = hh >= stop
            hit_tp = ll <= tp if tp is not None else np.zeros_like(hit_stop)
        opp = (short_sig if side == 1 else long_sig)[e:end + 1] if ex.opposite else np.zeros_like(hit_stop)
        first = lambda m: int(np.argmax(m)) if m.any() else 10**9
        js, jt, jo = first(hit_stop), first(hit_tp), first(opp)
        j = min(js, jt, jo, end - e)
        if j == js and js < 10**9:
            reason = "stop"
            gap = oo[j] < stop if side == 1 else oo[j] > stop
            xp = (oo[j] if gap and j > 0 else stop) * (1 - side * STOP_EXTRA * cost_mult)
            x = e + j
        elif j == jt and jt < 10**9:
            reason, xp, x = "tp", tp, e + j
        elif j == jo and jo < 10**9:
            reason = "opposite"
            x = min(e + j + 1, n - 1)          # signal on close of bar e+j -> exit next open
            xp = o[x]
        else:
            reason, x, xp = "time", end, c[end]
        gross = side * (xp / px - 1)
        f = side * fund[e:x + 1].sum()          # longs pay positive funding
        mae = (np.nanmin(l[e:x + 1]) / px - 1) if side == 1 else -(np.nanmax(h[e:x + 1]) / px - 1)
        out.append({"side": side, "entry_i": e, "exit_i": x, "entry_t": dates[e], "exit_t": dates[x],
                    "ret": gross - 2 * cost - f, "gross": gross, "funding": f, "mae": mae, "reason": reason,
                    "bars": x - e + 1})
        i = x + 1
    return out


def twin_returns(df: pd.DataFrame, trades: list[dict], rng: np.random.Generator, cost_mult: float = 1.0) -> np.ndarray:
    """Random-timing twin: same coin, side and holding length; entry bar drawn uniformly from the same period."""
    if not trades:
        return np.array([])
    o, c = df["open"].to_numpy(), df["close"].to_numpy()
    lo, hi = trades[0]["entry_i"], trades[-1]["exit_i"]
    cost = (FEE + SLIP) * cost_mult
    out = []
    for t in trades:
        b = t["bars"]
        if hi - b <= lo:
            continue
        e = int(rng.integers(lo, hi - b + 1))
        x = e + b - 1
        if not (np.isfinite(o[e]) and np.isfinite(c[x])) or o[e] <= 0:
            continue
        out.append(t["side"] * (c[x] / o[e] - 1) - 2 * cost)
    return np.array(out)
