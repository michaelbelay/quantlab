"""Fresh search batch B (REGISTER_B_2026-10-13.md). Point-in-time top-10, fit 2022-2024, test 2025-2026-09.

    .venv\\Scripts\\python.exe research\\fresh\\batch_b.py
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
FUT = ROOT / "data" / "market" / "dev_1h" / "binance" / "futures"
SIDE = 0.001
FIT0, FIT1 = pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC")
STABLE = {"USDC", "FDUSD", "TUSD", "BUSD", "USDP", "DAI", "EUR", "BTCDOM", "DEFI"}


def load(c: str, cols=("open", "high", "low", "close", "volume")) -> pd.DataFrame | None:
    p = FUT / f"{c}_USDT_USDT-1h-futures.feather"
    if not p.exists():
        return None
    d = pd.read_feather(p, columns=["date", *cols])
    d["date"] = pd.to_datetime(d["date"], utc=True)
    d = d.set_index("date").asfreq("1h").ffill()
    if "open" in cols:
        fp = FUT / f"{c}_USDT_USDT-1h-funding_rate.feather"
        d["fund"] = 0.0
        if fp.exists():
            f = pd.read_feather(fp)
            f["date"] = pd.to_datetime(f["date"], utc=True)
            d["fund"] = f.set_index("date")["funding_rate"].reindex(d.index).fillna(0.0)
    return d


# ---------------------------------------------------------------- universe: point-in-time top-10
val = {}
for p in FUT.glob("*_USDT_USDT-1h-futures.feather"):
    n = p.name.split("_")[0]
    if n in STABLE:
        continue
    x = load(n, ("close", "volume"))
    val[n] = (x["close"] * x["volume"]).resample("MS").sum()
V = pd.DataFrame(val)
TOP = {m: set(V.shift(1).loc[m].dropna().nlargest(10).index) for m in V.index[1:]}
USE = sorted(set().union(*TOP.values()))
D = {n: load(n) for n in USE}
print(f"universe: {len(USE)} coins were top-10 at some point", flush=True)


def in_top(n: str, t: pd.Timestamp) -> bool:
    return n in TOP.get(pd.Timestamp(t.year, t.month, 1, tz="UTC"), set())


def sim(n: str, i: int, d: int, bars: int, stop_px: float | None = None, entry: float | None = None):
    """Enter at bar i (open, or `entry` price inside bar i), hold up to `bars` bars, stop at price level.
    Returns (t_signal-free tuple pieces) t_in, t_out, net fraction."""
    x = D[n]
    j = min(i + bars, len(x)) - 1
    if j < i:
        return None
    o, h, l, c, fu = (x[k].to_numpy() for k in ("open", "high", "low", "close", "fund"))
    e = o[i] if entry is None else entry
    k_end, px = j, c[j]
    if stop_px is not None:
        for k in range(i, j + 1):
            if (d == 1 and l[k] <= stop_px) or (d == -1 and h[k] >= stop_px):
                k_end, px = k, (min(o[k], stop_px) if d == 1 else max(o[k], stop_px)) if k > i else stop_px
                break
    g = d * (px / e - 1)
    return x.index[i], x.index[k_end], g - 2 * SIDE - d * fu[i + 1:k_end + 1].sum()


def sigma24(x: pd.DataFrame) -> np.ndarray:
    return (np.log(x["close"]).diff().rolling(720, min_periods=500).std() * np.sqrt(24)).to_numpy()


def daily(x: pd.DataFrame) -> pd.DataFrame:
    return x.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})


def hour_idx(x: pd.DataFrame, t: pd.Timestamp) -> int:
    return int(x.index.searchsorted(t))


# ---------------------------------------------------------------- families -> list of (coin, t_sig, t_in, t_out, ret)
def f_dip(p, d_=1):
    """B0 (d_=1, dip in uptrend) and B3 (d_=-1, rip in downtrend)."""
    dip, hold, stop, tr = p
    out = []
    for n in USE:
        x = D[n]
        lc = np.log(x["close"]).to_numpy()
        sg = sigma24(x)
        r24 = lc - np.r_[np.full(24, np.nan), lc[:-24]]
        rtr = lc - np.r_[np.full(tr * 24, np.nan), lc[:-tr * 24]]
        cond = (d_ * rtr > 0) & (d_ * r24 <= -dip * sg)
        last = -10**9
        for i in np.flatnonzero(cond):
            if i - last < 24 or i + 2 > len(x) or not in_top(n, x.index[i]):
                continue
            last = i
            e = x["open"].iat[i + 1]
            r = sim(n, i + 1, d_, hold, stop_px=e * (1 - d_ * stop * sg[i]))
            if r:
                out.append((n, x.index[i], *r))
    return out


def weekly_pick(p, mode):
    """B1 (mode 'best') / B2 (mode 'worst') / B8 handled separately."""
    lb, hold_d = p
    out = []
    btc = D["BTC"]["close"]
    for t in pd.date_range("2021-03-01", "2026-09-14", freq="W-MON", tz="UTC"):
        if t not in btc.index or btc.asof(t - pd.Timedelta(hours=1)) <= btc.asof(t - pd.Timedelta(days=20)):
            continue
        cand = []
        for n in TOP.get(pd.Timestamp(t.year, t.month, 1, tz="UTC"), set()):
            c = D[n]["close"]
            a, b = c.asof(t - pd.Timedelta(hours=1)), c.asof(t - pd.Timedelta(days=lb))
            if np.isfinite(a) and np.isfinite(b) and b > 0 and t in D[n].index:
                cand.append((a / b - 1, n))
        cand.sort(reverse=(mode == "best"))
        for _, n in cand[:3]:
            r = sim(n, hour_idx(D[n], t), 1, hold_d * 24)
            if r:
                out.append((n, t, *r))
    return out


def f_flash(p):
    k, m, hold = p
    out = []
    for n in USE:
        x = D[n]
        r1 = np.log(x["close"]).diff()
        s1 = r1.rolling(720, min_periods=500).std().to_numpy()
        vavg = x["volume"].rolling(720, min_periods=500).mean().shift(1).to_numpy()
        sg = sigma24(x)
        cond = (r1.to_numpy() <= -k * s1) & (x["volume"].to_numpy() >= m * vavg)
        last = -10**9
        for i in np.flatnonzero(cond):
            if i - last < 24 or i + 2 > len(x) or not in_top(n, x.index[i]):
                continue
            last = i
            e = x["open"].iat[i + 1]
            r = sim(n, i + 1, 1, hold, stop_px=e * (1 - 2 * sg[i]))
            if r:
                out.append((n, x.index[i], *r))
    return out


def f_quiet(p):
    tr, hold, stop = p
    out = []
    for n in USE:
        x = D[n]
        dd = daily(x)
        down = dd["close"] < dd["close"].shift(1)
        low_v = dd["volume"] < dd["volume"].rolling(30).mean().shift(1)
        trend = dd["close"] / dd["close"].shift(tr) - 1 > 0
        cond = (down & low_v).rolling(3).sum().eq(3) & trend
        sg = sigma24(x)
        for t in dd.index[cond.fillna(False).to_numpy()]:
            te = t + pd.Timedelta(days=1)
            i = hour_idx(x, te)
            if i >= len(x) - 1 or not in_top(n, t):
                continue
            e = x["open"].iat[i]
            r = sim(n, i, 1, hold, stop_px=e * (1 - stop * sg[i - 1]))
            if r:
                out.append((n, t, *r))
    return out


def f_nr7(p):
    hold_d, = p
    out = []
    for n in USE:
        x = D[n]
        dd = daily(x)
        rng = dd["high"] - dd["low"]
        nr7 = rng <= rng.rolling(7).min()
        h, l = x["high"].to_numpy(), x["low"].to_numpy()
        for t in dd.index[nr7.fillna(False).to_numpy()]:
            if not in_top(n, t):
                continue
            H, L = dd.at[t, "high"], dd.at[t, "low"]
            i0 = hour_idx(x, t + pd.Timedelta(days=1))
            for i in range(i0, min(i0 + 24, len(x))):
                if h[i] > H or l[i] < L:
                    d_ = 1 if h[i] > H else -1                    # if both in one hour: the first listed (long)
                    lvl = H if d_ == 1 else L
                    e = max(x["open"].iat[i], lvl) if d_ == 1 else min(x["open"].iat[i], lvl)
                    r = sim(n, i, d_, hold_d * 24, stop_px=L if d_ == 1 else H, entry=e)
                    if r:
                        out.append((n, t, *r))
                    break
    return out


def f_turtle(p):
    ex_n, max_d = p
    out = []
    for n in USE:
        x = D[n]
        dd = daily(x)
        hi55, lo55 = dd["high"].rolling(55).max().shift(1), dd["low"].rolling(55).min().shift(1)
        hiN, loN = dd["high"].rolling(ex_n).max().shift(1), dd["low"].rolling(ex_n).min().shift(1)
        c = dd["close"]
        k, idx = 0, dd.index
        while k < len(dd) - 2:
            t = idx[k]
            d_ = 1 if c.iat[k] > hi55.iat[k] else (-1 if c.iat[k] < lo55.iat[k] else 0)
            if d_ == 0 or not in_top(n, t):
                k += 1
                continue
            j = k + 1
            while j < min(k + 1 + max_d, len(dd) - 1):
                if (d_ == 1 and c.iat[j] < loN.iat[j]) or (d_ == -1 and c.iat[j] > hiN.iat[j]):
                    break
                j += 1
            i_in, i_out = hour_idx(x, idx[k + 1]), hour_idx(x, idx[min(j + 1, len(dd) - 1)])
            r = sim(n, i_in, d_, max(1, i_out - i_in))
            if r:
                out.append((n, t, *r))
            k = j + 1
    return out


def f_beta(p):
    ma, hold_d = p
    out = []
    bd = daily(D["BTC"])["close"]
    m = bd.rolling(ma).mean()
    cross = (bd > m) & (bd.shift(1) <= m.shift(1)) & (bd / bd.shift(20) - 1 > 0)
    br = np.log(D["BTC"]["close"]).diff()
    for t in bd.index[cross.fillna(False).to_numpy()]:
        te = t + pd.Timedelta(days=1)
        cand = []
        for n in TOP.get(pd.Timestamp(t.year, t.month, 1, tz="UTC"), set()) - {"BTC"}:
            r = np.log(D[n]["close"]).diff()
            w = slice(te - pd.Timedelta(days=30), te - pd.Timedelta(hours=1))
            a, b = r.loc[w], br.loc[w]
            if len(a) > 500 and b.var() > 0:
                cand.append((a.cov(b) / b.var(), n))
        for _, n in sorted(cand, reverse=True)[:3]:
            i = hour_idx(D[n], te)
            r = sim(n, i, 1, hold_d * 24)
            if r:
                out.append((n, t, *r))
    return out


FAM = {
    "B0 dip in uptrend": (lambda p: f_dip(p, 1), list(itertools.product((1.5, 2.0, 2.5), (48, 72, 96), (1.5, 2.0, 3.0), (10, 20, 40)))),
    "B1 strength rotation": (lambda p: weekly_pick(p, "best"), [(lb, 7) for lb in (14, 30, 60)]),
    "B2 weekly losers": (lambda p: weekly_pick(p, "worst"), list(itertools.product((7, 14), (3, 7)))),
    "B3 rip in downtrend": (lambda p: f_dip((p[0], p[2], 3.0, p[1]), -1), list(itertools.product((1.5, 2.0, 2.5), (10, 20), (48, 72)))),
    "B4 flash dip": (f_flash, list(itertools.product((3, 4), (3, 5), (12, 24)))),
    "B5 quiet pullback": (f_quiet, list(itertools.product((10, 20), (72, 120), (2, 3)))),
    "B6 NR7 breakout": (f_nr7, [(2,), (4,)]),
    "B7 55d breakout": (f_turtle, list(itertools.product((10, 20), (20, 40)))),
    "B8 BTC trend alt beta": (f_beta, list(itertools.product((50, 100), (7, 14)))),
}


def frame(rows) -> pd.DataFrame:
    f = pd.DataFrame(rows, columns=["coin", "t", "t_in", "t_out", "ret"])
    f["ret"] = f["ret"] * 100
    return f[f.t >= FIT0]


def book(f: pd.DataFrame, slots: int = 3, start: float = 300.0):
    f = f.sort_values("t_in")
    taken = []
    for r in f.itertuples():
        if sum(1 for t_o, _ in taken if t_o > r.t_in) >= slots:
            continue
        eq_in = start + sum(p for t_o, p in taken if t_o <= r.t_in)
        taken.append((r.t_out, eq_in / slots * r.ret / 100))
    if not taken:
        return start, 0.0
    c = pd.Series([p for _, p in taken], index=[t for t, _ in taken]).sort_index().cumsum() + start
    return float(c.iloc[-1]), float((1 - c / c.cummax().clip(lower=start)).max())


res, chosen = {}, {}
for name, (fn, grid) in FAM.items():
    best = None
    for p in grid:
        f = frame(fn(p))
        fi = f[f.t < FIT1]
        eq, _ = book(fi)
        if best is None or eq > best[0]:
            best = (eq, p, f)
    eq_fit, p, f = best
    chosen[name] = f
    fi, te = f[f.t < FIT1], f[f.t >= FIT1]
    pf = te.ret[te.ret > 0].sum() / max(1e-9, -te.ret[te.ret < 0].sum()) if len(te) else 0
    yrs = {y: round(te[te.t.dt.year == y].ret.sum(), 1) for y in (2025, 2026)}
    eq_te, dd_te = book(te)
    ok = (len(te) >= 30 and te.ret.mean() > 0 and pf >= 1.2 and all(v > 0 for v in yrs.values())
          and len(fi) and fi.ret.mean() > 0 and eq_te > 300)
    res[name] = {"setting": p, "grid": len(grid), "fit_n": len(fi), "fit_avg": round(fi.ret.mean(), 2) if len(fi) else None,
                 "fit_account": round(eq_fit), "test_n": len(te), "test_avg": round(te.ret.mean(), 2) if len(te) else None,
                 "test_pf": round(pf, 2), "test_years": yrs, "test_account": round(eq_te), "test_drop_pct": round(dd_te * 100),
                 "pass": bool(ok)}
    r = res[name]
    print(f"{name:24} {str(p):22} fit n {r['fit_n']:4} {r['fit_avg'] or 0:+.2f}% acct {r['fit_account']:5} | test n "
          f"{r['test_n']:4} {r['test_avg'] or 0:+.2f}% PF {pf:4.2f} 2025 {yrs[2025]:+6.0f} 2026 {yrs[2026]:+6.0f} "
          f"acct {eq_te:5.0f} drop {dd_te*100:3.0f}% | {'PASS' if ok else 'fail'}", flush=True)

both = pd.concat([chosen["B0 dip in uptrend"], chosen["B3 rip in downtrend"]])
fi, te = both[both.t < FIT1], both[both.t >= FIT1]
eq_f, dd_f = book(fi)
eq_t, dd_t = book(te)
res["B9 dip+rip"] = {"fit_account": round(eq_f), "fit_drop_pct": round(dd_f * 100), "test_account": round(eq_t),
                     "test_drop_pct": round(dd_t * 100), "test_n": len(te), "test_avg": round(te.ret.mean(), 2)}
print(f"B9 dip+rip (B0 + B3 settings): fit acct {eq_f:.0f} drop {dd_f*100:.0f}% | test n {len(te)} {te.ret.mean():+.2f}% "
      f"acct {eq_t:.0f} drop {dd_t*100:.0f}%")
(HERE / "batch_b_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
