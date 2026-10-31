"""Batch Q (REGISTER_Q_2026-10-13.md): weekly cross-sectional anomalies on point-in-time top-30 (daily bars).

    .venv\\Scripts\\python.exe research\\fresh\\batch_q.py
"""
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FUT = ROOT / "data" / "market" / "dev_1h" / "binance" / "futures"
STABLE = {"USDC", "FDUSD", "TUSD", "BUSD", "USDP", "DAI", "EUR", "BTCDOM", "DEFI"}
SIDE = 0.001
FIT1, END = pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-09-21", tz="UTC")

O, C, TV, FU = {}, {}, {}, {}
for p in FUT.glob("*_USDT_USDT-1h-futures.feather"):
    n = p.name.split("_")[0]
    if n in STABLE:
        continue
    x = pd.read_feather(p, columns=["date", "open", "close", "volume"])
    x["date"] = pd.to_datetime(x["date"], utc=True)
    x = x.set_index("date")
    d = x.resample("1D").agg({"open": "first", "close": "last"})
    O[n], C[n] = d["open"], d["close"]
    TV[n] = (x["close"] * x["volume"]).resample("1D").sum()
    fp = FUT / f"{n}_USDT_USDT-1h-funding_rate.feather"
    if fp.exists():
        f = pd.read_feather(fp)
        f["date"] = pd.to_datetime(f["date"], utc=True)
        FU[n] = f.set_index("date")["funding_rate"].resample("1D").sum()
O, C, TV = pd.DataFrame(O), pd.DataFrame(C), pd.DataFrame(TV)
FU = pd.DataFrame(FU).reindex(C.index).fillna(0.0).reindex(columns=C.columns, fill_value=0.0)
TV = TV.where(TV > 0)
R = C.pct_change(fill_method=None)
MV = TV.resample("MS").sum(min_count=1)
TOP30 = {m: set(MV.shift(1).loc[m].dropna().nlargest(30).index) for m in MV.index[1:]}
print(f"{C.shape[1]} coins, daily {C.index[0].date()}..{C.index[-1].date()}", flush=True)


def score(kind, t, L, coins):
    w = R.loc[t - pd.Timedelta(days=L):t - pd.Timedelta(days=1), coins]
    w = w.loc[:, w.notna().sum() >= 0.9 * L]
    if kind == "max":
        return w.max()
    if kind == "skew":
        return w.skew()
    if kind == "vol":
        return w.std()
    if kind == "ivol":
        b = R.loc[w.index, "BTC"]
        beta = w.apply(lambda s: s.cov(b) / b.var())
        return (w - np.outer(b, beta)).std()
    if kind == "abvol":
        tv = TV.loc[t - pd.Timedelta(days=67):t - pd.Timedelta(days=1), w.columns]
        return tv.iloc[-7:].sum() / (tv.iloc[:60].mean() * 7)


def run(kind, L, N, hold, longonly=False, sign=1):
    """sign=1: long the LOW scores, short the HIGH; sign=-1: the reverse (Q4)."""
    eq, rows = 300.0, []
    t = pd.Timestamp("2021-12-27", tz="UTC")
    btc = C["BTC"]
    while t + pd.Timedelta(days=hold) <= END:
        m = pd.Timestamp(t.year, t.month, 1, tz="UTC")
        coins = [c for c in TOP30.get(m, ()) if np.isfinite(O.at[t, c]) if t in O.index]
        s = score(kind, t, L, coins).dropna() if coins else pd.Series(dtype=float)
        legs = []
        if longonly:
            if btc.asof(t - pd.Timedelta(days=1)) > btc.asof(t - pd.Timedelta(days=21)) and len(s) >= N:
                legs = [(c, 1) for c in s.nsmallest(N).index]
        elif len(s) >= 2 * N:
            s = s.sort_values()
            lo, hi = list(s.index[:N]), list(s.index[-N:])
            legs = [(c, sign) for c in lo] + [(c, -sign) for c in hi]
        pnl = 0.0
        t2 = t + pd.Timedelta(days=hold)
        for c, d in legs:
            e = O.at[t, c]
            px = O[c].loc[:t2].ffill().iloc[-1]
            px = C[c].loc[:t2].ffill().iloc[-1] if not np.isfinite(px) else px
            fu = FU[c].loc[t:t2 - pd.Timedelta(days=1)].sum()
            pnl += eq / len(legs) * (d * (px / e - 1) - 2 * SIDE - d * fu)
        rows.append((t, pnl, eq))
        eq += pnl
        t = t2
    f = pd.DataFrame(rows, columns=["t", "pnl", "eq_in"])
    return f


def acct(f):
    if f.empty:
        return 300.0, 0.0
    c = 300.0 + f.pnl.cumsum()
    c = pd.concat([pd.Series([300.0]), c])
    return float(c.iloc[-1]), float((1 - c / c.cummax()).max())


def split(f):
    fi, te = f[f.t < FIT1].copy(), f[f.t >= FIT1].copy()
    te["pnl"] = te.pnl * 300.0 / te.eq_in.iloc[0] if len(te) else te.pnl  # restart test at 300
    return fi, te


FAMQ = {
    "Q1 MAX effect": ("max", 1, False),
    "Q2 idiosyncratic vol": ("ivol", 1, False),
    "Q3 skewness": ("skew", 1, False),
    "Q4 abnormal volume": ("abvol", -1, False),
    "Q5 low-vol long-only": ("vol", 1, True),
}
res = {}
for name, (kind, sign, lo) in FAMQ.items():
    grid = list(itertools.product((7,) if kind == "abvol" else (30, 60), (3, 5), (7, 14)))
    best, pos = None, 0
    for L, N, hold in grid:
        f = run(kind, L, N, hold, lo, sign)
        fi, te = split(f)
        ef, _ = acct(fi)
        et, _ = acct(te)
        pos += et > 300
        if best is None or ef > best[0]:
            best = (ef, (L, N, hold), f)
    ef, p, f = best
    fi, te = split(f)
    ef, df_ = acct(fi)
    et, dt = acct(te)
    yrs = {y: round(g.pnl.sum(), 1) for y, g in te.groupby(te.t.dt.year)}
    ok = et > 300 and te.pnl.mean() > 0 and yrs.get(2025, 0) > 0 and yrs.get(2026, 0) > 0 and ef > 300 \
        and pos >= len(grid) / 2 and dt <= 0.35
    res[name] = {"setting(L,N,hold)": p, "fit_account": round(ef), "fit_drop_pct": round(df_ * 100),
                 "test_account": round(et), "test_drop_pct": round(dt * 100), "test_years_usdt": yrs,
                 "grid_positive_on_test": f"{pos}/{len(grid)}", "pass": bool(ok)}
    print(f"{name:22} {str(p):12} fit acct {ef:6.0f} drop {df_*100:3.0f}% | test acct {et:5.0f} drop {dt*100:3.0f}% "
          f"{yrs} | grid+ {pos}/{len(grid)} | {'PASS' if ok else 'fail'}", flush=True)
(Path(__file__).parent / "batch_q_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
