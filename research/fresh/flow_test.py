"""Order-flow families F1-F5 (REGISTER_F_2026-10-13.md). Reuses batch_b.py's universe, simulator and account."""
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

src = (Path(__file__).parent / "batch_b.py").read_text(encoding="utf-8")
exec(src[:src.index("res, chosen = {}, {}")])
FLOW = ROOT / "data" / "market" / "flow"

have = []
for n in USE:
    f = FLOW / f"{n}.feather"
    if not f.exists():
        continue
    q = pd.read_feather(f).drop_duplicates("date").set_index("date")
    x = D[n]
    x["qv"] = q["quote_volume"].reindex(x.index).fillna(0.0)
    x["tbq"] = q["taker_buy_quote"].reindex(x.index).fillna(0.0)
    have.append(n)
print(f"flow data for {len(have)}/{len(USE)} coins", flush=True)


def share_z(x, w):
    s = x["tbq"].rolling(w).sum() / x["qv"].rolling(w).sum().replace(0, np.nan)
    return ((s - s.rolling(720, min_periods=500).mean()) / s.rolling(720, min_periods=500).std()).to_numpy()


def run_events(n, x, cond, d_, hold, stop_k, out):
    sg = sigma24(x)
    last = -10**9
    for i in np.flatnonzero(cond):
        if i - last < 24 or i + 2 > len(x) or not in_top(n, x.index[i]) or not np.isfinite(sg[i]):
            continue
        last = i
        e = x["open"].iat[i + 1]
        r = sim(n, i + 1, d_, hold, stop_px=e * (1 - d_ * stop_k * sg[i]))
        if r:
            out.append((n, x.index[i], *r))


def f1(p):
    w, k, hold = p
    out = []
    for n in have:
        x = D[n]
        z = share_z(x, w)
        run_events(n, x, z >= k, 1, hold, 2, out)
        run_events(n, x, z <= -k, -1, hold, 2, out)
    return out


def f2(p):
    k, hold = p
    out = []
    for n in have:
        x = D[n]
        z, sg = share_z(x, 24), sigma24(x)
        lc = np.log(x["close"]).to_numpy()
        r24 = lc - np.r_[np.full(24, np.nan), lc[:-24]]
        run_events(n, x, (r24 <= -sg) & (z >= k), 1, hold, 2, out)
        run_events(n, x, (r24 >= sg) & (z <= -k), -1, hold, 2, out)
    return out


def f3(p):
    k, hold = p
    out = []
    for n in have:
        x = D[n]
        z = share_z(x, 24)
        lc = np.log(x["close"]).to_numpy()
        r10 = lc - np.r_[np.full(240, np.nan), lc[:-240]]
        run_events(n, x, (r10 > 0) & (z >= k), 1, hold, 2, out)
        run_events(n, x, (r10 < 0) & (z <= -k), -1, hold, 2, out)
    return out


def f4(p):
    hold, = p
    out = []
    net = {}
    for n in have:
        x = D[n]
        q = x["qv"].rolling(24).sum().replace(0, np.nan)
        net[n] = ((2 * x["tbq"].rolling(24).sum() - x["qv"].rolling(24).sum()) / q)
    N = pd.DataFrame(net)
    for t in pd.date_range("2021-03-01", "2026-09-18", freq="1D", tz="UTC"):
        tops = [n for n in TOP.get(pd.Timestamp(t.year, t.month, 1, tz="UTC"), set()) if n in N.columns]
        if len(tops) < 6 or t not in N.index:
            continue
        row = N.loc[t - pd.Timedelta(hours=1), tops].dropna().sort_values()
        if len(row) < 6:
            continue
        for n, d_ in [(c, -1) for c in row.index[:2]] + [(c, 1) for c in row.index[-2:]]:
            r = sim(n, hour_idx(D[n], t), d_, hold)
            if r:
                out.append((n, t, *r))
    return out


def f5(p):
    k, hold = p
    out = []
    for n in have:
        x = D[n]
        z = share_z(x, 4)
        lc = np.log(x["close"]).to_numpy()
        s1 = pd.Series(lc).diff().rolling(720, min_periods=500).std().to_numpy()
        r4 = lc - np.r_[np.full(4, np.nan), lc[:-4]]
        run_events(n, x, (z <= -k) & (r4 <= -2 * 2 * s1), 1, hold, 2, out)
        run_events(n, x, (z >= k) & (r4 >= 2 * 2 * s1), -1, hold, 2, out)
    return out


FAMF = {
    "F1 flow continuation": (f1, list(itertools.product((4, 12), (2, 3), (8, 24)))),
    "F2 absorption": (f2, list(itertools.product((1.5, 2), (24, 48)))),
    "F3 flow in trend": (f3, list(itertools.product((1, 1.5, 2), (24, 48)))),
    "F4 flow rank neutral": (f4, [(24,), (72,)]),
    "F5 exhaustion": (f5, list(itertools.product((3, 4), (12, 24)))),
}
res = {}
for name, (fn, grid) in FAMF.items():
    rows, best = [], None
    for p in grid:
        f = frame(fn(p))
        fi, te = f[f.t < FIT1], f[f.t >= FIT1]
        eqf, _ = book(fi)
        rows.append((p, len(te), te.ret.mean() if len(te) else np.nan))
        if best is None or eqf > best[0]:
            best = (eqf, p, f)
    eqf, p, f = best
    fi, te = f[f.t < FIT1], f[f.t >= FIT1]
    pf = te.ret[te.ret > 0].sum() / max(1e-9, -te.ret[te.ret < 0].sum()) if len(te) else 0
    yrs = {y: round(te[te.t.dt.year == y].ret.sum(), 1) for y in (2025, 2026)}
    eqt, ddt = book(te)
    pos = sum(1 for _, n_, a in rows if n_ and a > 0)
    ok = (len(te) >= 30 and te.ret.mean() > 0 and pf >= 1.2 and all(v > 0 for v in yrs.values())
          and len(fi) and fi.ret.mean() > 0 and eqt > 300)
    res[name] = {"setting": p, "fit_n": len(fi), "fit_avg": round(fi.ret.mean(), 2), "fit_account": round(eqf),
                 "test_n": len(te), "test_avg": round(te.ret.mean(), 2), "test_pf": round(pf, 2), "test_years": yrs,
                 "test_account": round(eqt), "test_drop_pct": round(ddt * 100),
                 "grid_positive_on_test": f"{pos}/{len(grid)}", "pass": bool(ok),
                 "grid": [(str(a), b, None if np.isnan(c) else round(c, 2)) for a, b, c in rows]}
    print(f"{name:22} {str(p):16} fit n {len(fi):4} {fi.ret.mean():+.2f}% acct {eqf:5.0f} | test n {len(te):4} "
          f"{te.ret.mean():+.2f}% PF {pf:4.2f} 2025 {yrs[2025]:+5.0f} 2026 {yrs[2026]:+5.0f} acct {eqt:5.0f} "
          f"drop {ddt*100:3.0f}% | grid+ {pos}/{len(grid)} | {'PASS' if ok else 'fail'}", flush=True)
(Path(__file__).parent / "flow_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
