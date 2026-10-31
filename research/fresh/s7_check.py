"""S7 'dip in uptrend' - checks after it passed the registered bar (2026-10-13). Changes nothing.

1. per coin and per year (registered rule)
2. neighbours: dip 1.5/2/2.5 sigma x hold 48/72/96h x stop 1.5/2/3 sigma x trend 10/20/40 days (all reported)
3. point-in-time top-10 coins by 30-day traded value (all futures coins on disk, re-ranked monthly) instead of 5 fixed
4. a 300 USDT account: max 3 open, each equity/3, 1x and 2x, positions in a crash overlap -> real drawdown
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
FUT = ROOT / "data" / "market" / "dev_1h" / "binance" / "futures"
SIDE = 0.001
FIT_END = pd.Timestamp("2024-01-01", tz="UTC")
STABLE = {"USDC", "FDUSD", "TUSD", "BUSD", "USDP", "DAI", "EUR", "BTCDOM", "DEFI"}


def load(c: str) -> pd.DataFrame | None:
    p = FUT / f"{c}_USDT_USDT-1h-futures.feather"
    if not p.exists():
        return None
    d = pd.read_feather(p)
    d["date"] = pd.to_datetime(d["date"], utc=True)
    d = d.set_index("date").asfreq("1h").ffill()
    fp = FUT / f"{c}_USDT_USDT-1h-funding_rate.feather"
    if fp.exists():
        f = pd.read_feather(fp)
        f["date"] = pd.to_datetime(f["date"], utc=True)
        d["fund"] = f.set_index("date")["funding_rate"].reindex(d.index).fillna(0.0)
    else:
        d["fund"] = 0.0
    return d


def signals(x: pd.DataFrame, dip=2.0, hold=72, stop=2.0, trend_d=20) -> list[tuple]:
    """(signal time, entry time, exit time, net fraction) for one coin."""
    lc = np.log(x["close"])
    sig = (lc.diff().rolling(720, min_periods=500).std() * np.sqrt(24)).to_numpy()
    r24 = (lc - lc.shift(24)).to_numpy()
    rtr = (x["close"] / x["close"].shift(trend_d * 24) - 1).to_numpy()
    o, h, l, c, fu = (x[k].to_numpy() for k in ("open", "high", "low", "close", "fund"))
    cond = (rtr > 0) & (r24 <= -dip * sig)
    out, last = [], -10**9
    for i in np.flatnonzero(cond):
        if i - last < 24 or i + 1 + hold > len(x):
            continue
        last = i
        e, s = o[i + 1], stop * sig[i]
        k_end, g = i + hold, c[i + hold] / e - 1
        for k in range(i + 1, i + 1 + hold):
            if 1 - l[k] / e >= s:
                k_end, g = k, -s
                break
        net = g - 2 * SIDE - fu[i + 2:k_end + 1].sum()
        out.append((x.index[i], x.index[i + 1], x.index[k_end], net))
    return out


def summary(df: pd.DataFrame) -> str:
    te, fi = df[df.t >= FIT_END], df[df.t < FIT_END]
    pf = te.ret[te.ret > 0].sum() / max(1e-9, -te.ret[te.ret < 0].sum())
    ys = " ".join(f"{y}:{te[te.t.dt.year == y].ret.sum():+5.0f}" for y in (2024, 2025, 2026))
    return (f"fit n {len(fi):4} avg {fi.ret.mean():+.2f}% | test n {len(te):4} avg {te.ret.mean():+.2f}% PF {pf:4.2f} | {ys}")


def frame(rows) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["coin", "t", "t_in", "t_out", "ret"]).assign(ret=lambda d: d.ret * 100)


COINS = ["BTC", "ETH", "BNB", "SOL", "XRP"]
D = {c: load(c) for c in COINS}

print("1. registered rule, per coin")
base = frame([(c, *s) for c in COINS for s in signals(D[c])])
for c, g in base.groupby("coin"):
    print(f"   {c:4} {summary(g)}")
print(f"   ALL  {summary(base)}")
print("   per year, all coins:", base.groupby(base.t.dt.year).ret.agg(["count", "sum"]).round(1).to_dict("index"))

print("\n2. neighbours (test window 2024-2026)")
grid = []
for dip, hold, stop, tr in itertools.product((1.5, 2.0, 2.5), (48, 72, 96), (1.5, 2.0, 3.0), (10, 20, 40)):
    f = frame([(c, *s) for c in COINS for s in signals(D[c], dip, hold, stop, tr)])
    te, fi = f[f.t >= FIT_END], f[f.t < FIT_END]
    grid.append((dip, hold, stop, tr, len(fi), fi.ret.mean(), len(te), te.ret.mean(),
                 te.ret[te.ret > 0].sum() / max(1e-9, -te.ret[te.ret < 0].sum())))
G = pd.DataFrame(grid, columns=["dip", "hold", "stop", "trend_d", "fit_n", "fit_avg", "test_n", "test_avg", "test_pf"])
print(f"   {len(G)} settings: test avg > 0 in {(G.test_avg > 0).sum()}, fit avg > 0 in {(G.fit_avg > 0).sum()}, "
      f"both in {((G.test_avg > 0) & (G.fit_avg > 0)).sum()}; median test avg {G.test_avg.median():+.2f}%, "
      f"median test PF {G.test_pf.median():.2f}")
for k in ("dip", "hold", "stop", "trend_d"):
    print(f"   by {k:7}:", G.groupby(k).test_avg.median().round(2).to_dict())
G.to_csv(HERE / "s7_grid.csv", index=False)

print("\n3. point-in-time top-10 by 30-day traded value (re-ranked each month)")
names = sorted({p.name.split("_")[0] for p in FUT.glob("*_USDT_USDT-1h-futures.feather")} - STABLE)
val = {}
for n in names:
    x = load(n)
    if x is None:
        continue
    val[n] = (x["close"] * x["volume"]).resample("MS").sum()
V = pd.DataFrame(val)
top = {m: set(V.shift(1).loc[m].dropna().nlargest(10).index) for m in V.index[1:]}   # last month's value -> this month
rows = []
for n in sorted(set().union(*top.values())):
    x = D[n] if n in D else load(n)
    for s in signals(x):
        m = pd.Timestamp(s[0].year, s[0].month, 1, tz="UTC")
        if n in top.get(m, set()):
            rows.append((n, *s))
pit = frame(rows)
print(f"   coins used: {pit.coin.nunique()}  {summary(pit)}")
print("   per year:", pit.groupby(pit.t.dt.year).ret.agg(["count", "sum"]).round(1).to_dict("index"))


def book(f: pd.DataFrame, lev: float, slots: int = 3, start: float = 300.0) -> tuple[float, float, dict]:
    """Trades in entry order, max `slots` open, each sized equity/slots x lev where equity = start + closed P&L at
    the entry time (no look-ahead). Drawdown on the equity curve at each trade close."""
    f = f.sort_values("t_in")
    taken = []                                                  # (t_out, pnl)
    for r in f.itertuples():
        if sum(1 for t_o, _ in taken if t_o > r.t_in) >= slots:
            continue
        eq_in = start + sum(p for t_o, p in taken if t_o <= r.t_in)
        taken.append((r.t_out, eq_in / slots * lev * r.ret / 100))
    if not taken:
        return start, 0.0, {}
    c = pd.Series([p for _, p in taken], index=[t for t, _ in taken]).sort_index().cumsum() + start
    dd = float((1 - c / c.cummax().clip(lower=start)).max())
    return float(c.iloc[-1]), dd, c.groupby(c.index.year).last().round(0).to_dict()

print("\n4. 300 USDT account, 3 slots (equity/3 each), 2021 -> 2026-09")
for lab, f in (("5 majors", base), ("top-10 point in time", pit)):
    for lev in (1, 2):
        eq, dd, yr = book(f, lev)
        print(f"   {lab:22} {lev}x: 300 -> {eq:7.0f}  max drop {dd * 100:4.0f}%  year-end {yr}")
