"""Statistics for the pipeline gates. Standard library + numpy/pandas only."""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pandas as pd

N = NormalDist()
EULER = 0.5772156649


def t_stat(pnl: np.ndarray) -> float | None:
    """t-statistic of the mean trade result against zero."""
    if len(pnl) < 3:
        return None
    sd = float(np.std(pnl, ddof=1))
    return float(np.mean(pnl) / sd * math.sqrt(len(pnl))) if sd > 0 else None


def daily_series(df: pd.DataFrame) -> pd.Series:
    """Daily P&L (by exit day), zero-filled across the whole span."""
    s = df.groupby(df["exit_date"].dt.floor("D")).pnl.sum()
    if s.empty:
        return s
    return s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="D", tz="UTC"), fill_value=0.0)


def sharpe_parts(daily: pd.Series):
    """Per-period Sharpe, skewness, (Pearson) kurtosis, number of periods."""
    x = daily.to_numpy(float)
    if len(x) < 30 or x.std(ddof=1) == 0:
        return None
    sr = x.mean() / x.std(ddof=1)
    z = (x - x.mean()) / x.std(ddof=0)
    return sr, float((z ** 3).mean()), float((z ** 4).mean()), len(x)


def deflated_sharpe(sr: float, skew: float, kurt: float, T: int, n_trials: int, sr_var: float) -> float:
    """Probability that the true Sharpe exceeds the best Sharpe expected from n_trials of noise.

    Bailey & Lopez de Prado (2014). sr is per-period (daily); sr_var is the variance of
    per-period Sharpe ratios across the trials.
    """
    n_trials = max(int(n_trials), 2)
    sr0 = math.sqrt(max(sr_var, 1e-12)) * ((1 - EULER) * N.inv_cdf(1 - 1 / n_trials)
                                           + EULER * N.inv_cdf(1 - 1 / (n_trials * math.e)))
    den = 1 - skew * sr + (kurt - 1) / 4 * sr ** 2
    if den <= 0 or T < 2:
        return 0.0
    return float(N.cdf((sr - sr0) * math.sqrt(T - 1) / math.sqrt(den)))


def random_entry_totals(rng: np.random.Generator, f_open: np.ndarray, f_close: np.ndarray, trades: list,
                        reps: int, fee_slip: float, start: int = 250) -> np.ndarray:
    """Total P&L of `reps` random-entry replicas of one coin's trades.

    Each replica keeps every trade's side, size and holding time but moves its entry to a
    random bar. Costs are charged like the backtester (fee + slippage both sides).
    Funding is ignored for the replicas (it is small and would only make the bar easier).
    """
    n = len(f_close)
    out = np.zeros(reps)
    for t in trades:
        hold = max(1, t.bars)
        hi = n - hold - 2
        if hi <= start:
            continue
        e = rng.integers(start, hi, size=reps)
        entry = f_open[e + 1]
        exit_ = f_close[e + 1 + hold - 1]
        ret = t.side * (exit_ / entry - 1)
        out += (ret - 2 * fee_slip) * t.notional
    return out


def portfolio(df: pd.DataFrame, slots: int = 10, start_equity: float = 1000.0,
              max_same_side: int | None = None) -> dict:
    """Equity-compounding portfolio: at most `slots` positions, stake = equity/slots.

    Trades are taken in entry order when a slot is free (and, with `max_same_side`, when
    fewer than that many positions are open in the same direction - the live account's
    MAX_SAME_DIRECTION rule); each trade's return on its own notional is applied to its
    stake at exit.
    """
    if df.empty:
        return {"ret_pct": 0.0, "max_dd": 0.0, "taken": 0, "skipped": 0}
    d = df.sort_values("entry_date")
    rets = (d["pnl"] / d["notional"]).to_numpy()
    ent, ex = d["entry_date"].to_numpy(), d["exit_date"].to_numpy()
    side = (d["side"] == "long").to_numpy()
    equity, peak, max_dd = start_equity, start_equity, 0.0
    open_: list[tuple] = []           # (exit_time, stake, ret, is_long)
    taken = skipped = 0
    for i in range(len(d)):
        open_.sort(key=lambda x: x[0])
        while open_ and open_[0][0] <= ent[i]:
            _, stake, r, _ = open_.pop(0)
            equity += stake * r
            peak = max(peak, equity)
            max_dd = max(max_dd, (peak - equity) / peak if peak > 0 else 0)
        same = sum(1 for o in open_ if o[3] == side[i]) if max_same_side else 0
        if len(open_) < slots and equity > 0 and (not max_same_side or same < max_same_side):
            open_.append((ex[i], equity / slots, rets[i], side[i]))
            taken += 1
        else:
            skipped += 1
    for _, stake, r, _ in sorted(open_, key=lambda x: x[0]):
        equity += stake * r
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak if peak > 0 else 0)
    return {"ret_pct": round((equity / start_equity - 1) * 100, 1), "max_dd": round(max_dd * 100, 1),
            "taken": taken, "skipped": skipped}


def entry_keys(df: pd.DataFrame) -> set:
    """(coin, entry day, side) keys used to measure overlap between strategies."""
    return set(zip(df["pair"], df["entry_date"].dt.floor("D").astype("int64"), df["side"]))


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0
