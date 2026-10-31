"""Batch S (REGISTER_S_2026-10-13.md): shock-and-settle on 5m price + open interest.

    .venv\\Scripts\\python.exe research\\fresh\\shock.py
"""
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FUT = ROOT / "data" / "market" / "dev_1h" / "binance" / "futures"
OI = ROOT / "data" / "market" / "open_interest"
SIDE, LEV, MMR, MAXPOS = 0.001, 5.0, 0.01, 2
FIT0, FIT1 = pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC")
STABLE = {"USDC", "FDUSD", "TUSD", "BUSD", "USDP", "DAI", "EUR", "BTCDOM", "DEFI"}

val = {}
for p in FUT.glob("*_USDT_USDT-1h-futures.feather"):
    n = p.name.split("_")[0]
    if n in STABLE:
        continue
    x = pd.read_feather(p, columns=["date", "close", "volume"])
    x["date"] = pd.to_datetime(x["date"], utc=True)
    val[n] = (x.set_index("date")["close"] * x.set_index("date")["volume"]).resample("MS").sum()
V = pd.DataFrame(val)
TOP = {m: set(V.shift(1).loc[m].dropna().nlargest(10).index) for m in V.index[1:]}

D = {}
for f in sorted(OI.glob("*.feather")):
    x = pd.read_feather(f).set_index("date").sort_index()
    x = x[~x.index.duplicated()]
    full = pd.date_range(x.index[0], x.index[-1], freq="5min")
    x = x.reindex(full)                                     # gaps stay NaN (months not downloaded)
    x["lc"] = np.log(x["close"])
    x["sig5"] = x["lc"].diff().rolling(8640, min_periods=6000).std().shift(1)
    x["month"] = x.index.to_period("M").to_timestamp().tz_localize("UTC")
    x["top"] = [f.stem in TOP.get(m, set()) for m in x["month"]]
    D[f.stem] = x
print(f"{len(D)} coins with 5m price + OI", flush=True)


def events(p):
    W, k, o, H = p
    nb, hb = W // 5, H // 5
    out = []
    for n, x in D.items():
        lc, oi = x["lc"].to_numpy(), x["oi"].to_numpy()
        op, hi, lo, cl = (x[c].to_numpy() for c in ("open", "high", "low", "close"))
        rW = lc - np.r_[np.full(nb, np.nan), lc[:-nb]]
        sW = x["sig5"].to_numpy() * np.sqrt(nb)
        oW = oi / np.r_[np.full(nb, np.nan), oi[:-nb]] - 1
        top = x["top"].to_numpy()
        for d in (1, -1):
            cond = (d * rW <= -k * sW) & (oW <= -o / 100) & top
            last = -10**9
            for i in np.flatnonzero(cond):
                if i - last < 48 or i + 14 + hb >= len(x):
                    continue
                last = i
                s0 = cl[i - nb]
                ext = lo[i - nb + 1:i + 1].min() if d == 1 else hi[i - nb + 1:i + 1].max()
                for j in range(i + 1, i + 13):
                    ext = min(ext, lo[j]) if d == 1 else max(ext, hi[j])
                    size = abs(s0 - ext)
                    if size > 0 and d * (cl[j] - ext) >= 0.25 * size:
                        e = op[j + 1]
                        stop = ext - d * 0.1 * size
                        R = d * (e - stop)
                        if not np.isfinite(e) or R <= 0:
                            break
                        tgt = e + d * 2 * R
                        px, kk = cl[j + hb], j + hb
                        for kk in range(j + 1, j + 1 + hb):
                            if (d == 1 and lo[kk] <= stop) or (d == -1 and hi[kk] >= stop):
                                px = stop if kk > j + 1 else (min(op[kk], stop) if d == 1 else max(op[kk], stop))
                                break
                            if (d == 1 and hi[kk] >= tgt) or (d == -1 and lo[kk] <= tgt):
                                px = tgt
                                break
                        ret = max(d * (px / e - 1) - 2 * SIDE, -1 / LEV)
                        if np.isfinite(ret):
                            out.append((n, x.index[i], x.index[j + 1], x.index[kk], ret, R / e, d))
                        break
    f = pd.DataFrame(out, columns=["coin", "t", "t_in", "t_out", "ret", "sd", "side"])
    return f[f.t >= FIT0]


def book(f, risk=0.01, start=300.0):
    f = f.sort_values("t_in")
    taken = []
    for r in f.itertuples():
        if sum(1 for t_o, _ in taken if t_o > r.t_in) >= MAXPOS or r.sd >= 1 / LEV - MMR - 0.01:
            continue
        eq = start + sum(p for t_o, p in taken if t_o <= r.t_in)
        notional = min(risk * eq / r.sd, LEV * eq / MAXPOS)
        if notional >= 5:
            taken.append((r.t_out, notional * r.ret))
    if not taken:
        return start, 0.0
    c = pd.Series([p for _, p in taken], index=[t for t, _ in taken]).sort_index().cumsum() + start
    return float(c.iloc[-1]), float((1 - c / c.cummax().clip(lower=start)).max())


def line(lab, f):
    fi, te = f[f.t < FIT1], f[f.t >= FIT1]
    pf = te.ret[te.ret > 0].sum() / max(1e-9, -te.ret[te.ret < 0].sum()) if len(te) else 0
    et, dt = book(te)
    et2, dt2 = book(te, 0.02)
    yrs = {int(y): round(g.ret.sum() * 100, 1) for y, g in f.groupby(f.t.dt.year)}
    print(f"  {lab:7} fit n {len(fi):4} {fi.ret.mean()*100 if len(fi) else 0:+.2f}% | test n {len(te):4} "
          f"{te.ret.mean()*100 if len(te) else 0:+.2f}% PF {pf:4.2f} acct1% {et:6.1f} drop {dt*100:4.1f}% acct2% {et2:6.1f} "
          f"drop {dt2*100:4.1f}% | stop {te.sd.median()*100 if len(te) else 0:.1f}% | {yrs}", flush=True)
    return {"fit_n": len(fi), "fit_avg_pct": round(fi.ret.mean() * 100, 3) if len(fi) else None, "test_n": len(te),
            "test_avg_pct": round(te.ret.mean() * 100, 3) if len(te) else None, "test_pf": round(pf, 2),
            "test_account_1pct": round(et, 1), "test_drop_pct": round(dt * 100, 1), "test_account_2pct": round(et2, 1),
            "years_sum_pct": yrs}


GRID = list(itertools.product((15, 30), (3, 4), (1, 2), (60, 240)))
cache = {}
for p in GRID:
    f = events(p)
    cache[p] = f
    fi, te = f[f.t < FIT1], f[f.t >= FIT1]
    print(f"{p}: fit n {len(fi)} {fi.ret.mean()*100 if len(fi) else 0:+.2f}% | test n {len(te)} "
          f"{te.ret.mean()*100 if len(te) else 0:+.2f}% (long {te[te.side==1].ret.mean()*100 if (te.side==1).any() else 0:+.2f}% "
          f"n {(te.side==1).sum()}, short {te[te.side==-1].ret.mean()*100 if (te.side==-1).any() else 0:+.2f}% n {(te.side==-1).sum()})",
          flush=True)

out = {}
for lab, sel in (("both", None), ("long", 1), ("short", -1)):
    sub = {p: (f if sel is None else f[f.side == sel]) for p, f in cache.items()}
    best = max(GRID, key=lambda p: book(sub[p][sub[p].t < FIT1])[0])
    pos = sum(1 for p in GRID if (sub[p].t >= FIT1).any() and sub[p][sub[p].t >= FIT1].ret.mean() > 0)
    print(f"\n{lab}: chosen on fit {best}, settings positive on test {pos}/{len(GRID)}", flush=True)
    r = line(lab, sub[best])
    te = sub[best][sub[best].t >= FIT1]
    y = r["years_sum_pct"]
    r["pass"] = bool(r["test_n"] >= 30 and (r["test_avg_pct"] or 0) > 0 and r["test_pf"] >= 1.2
                     and y.get(2025, 0) > 0 and y.get(2026, 0) > 0 and r["test_account_1pct"] > 300
                     and (r["fit_avg_pct"] or 0) > 0 and pos >= 8)
    r["setting"], r["grid_positive_on_test"] = best, f"{pos}/{len(GRID)}"
    print(f"  -> {'PASS' if r['pass'] else 'fail'}", flush=True)
    out[lab] = r
(Path(__file__).parent / "shock_results.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
