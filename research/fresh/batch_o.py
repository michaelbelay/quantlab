"""Batch O (REGISTER_O_2026-10-13.md): open-interest positioning families at 1h. Reuses flow_test.py / batch_b.py."""
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

src = (Path(__file__).parent / "flow_test.py").read_text(encoding="utf-8")
exec(src[:src.index("FAMF = {")])
OID = ROOT / "data" / "market" / "open_interest"
SLOTS = 6

oi_have = []
for n in have:
    f = OID / f"{n}.feather"
    if not f.exists():
        continue
    q = pd.read_feather(f).set_index("date").sort_index()
    o = q["oi"].resample("1h").last()
    D[n]["oi"] = o.reindex(D[n].index)
    oi_have.append(n)
print(f"OI for {len(oi_have)} coins", flush=True)


def z(s, w=720, mp=400):
    return ((s - s.rolling(w, min_periods=mp).mean()) / s.rolling(w, min_periods=mp).std()).to_numpy()


PRE = {}
for n in oi_have:
    x = D[n]
    lc = np.log(x["close"])
    PRE[n] = {
        "zoi": z(np.log(x["oi"]).diff(24)),
        "r10": (lc - lc.shift(240)).to_numpy(),
        "r24": (lc - lc.shift(24)).to_numpy(),
        "sg": sigma24(x),
        "zf": z(x["fund"].rolling(24).mean(), 720, 400),
        "zflow": share_z(x, 24),
    }


def fam(make, hold, stop):
    out = []
    for n in oi_have:
        x, p = D[n], PRE[n]
        lo, sh = make(p)
        run_events(n, x, lo, 1, hold, stop, out)
        run_events(n, x, sh, -1, hold, stop, out)
    return out


def o1(p):
    k, h = p
    return fam(lambda q: ((q["r10"] > 0) & (q["r24"] > 0) & (q["zoi"] >= k),
                          (q["r10"] < 0) & (q["r24"] < 0) & (q["zoi"] >= k)), h, 2)


def o2(p):
    k, h = p
    return fam(lambda q: ((q["r10"] > 0) & (q["r24"] <= -q["sg"]) & (q["zoi"] >= k),
                          (q["r10"] < 0) & (q["r24"] >= q["sg"]) & (q["zoi"] >= k)), h, 2)


def o3(p):
    k, h = p
    return fam(lambda q: ((q["r10"] > 0) & (q["r24"] <= -q["sg"]) & (q["zoi"] <= -k),
                          (q["r10"] < 0) & (q["r24"] >= q["sg"]) & (q["zoi"] <= -k)), h, 3)


def o4(p):
    k, h = p
    return fam(lambda q: ((q["r10"] > 0) & (q["zf"] <= -k), (q["r10"] < 0) & (q["zf"] >= k)), h, 2)


def o5(p):
    k, = p
    return fam(lambda q: ((q["r10"] > 0) & (q["zflow"] >= 1.5) & (q["zoi"] >= k),
                          (q["r10"] < 0) & (q["zflow"] <= -1.5) & (q["zoi"] >= k)), 48, 2)


FAMO = {
    "O1 new money in trend": (o1, list(itertools.product((1.5, 2), (24, 48)))),
    "O2 trapped vs trend": (o2, list(itertools.product((1.5, 2), (24, 48)))),
    "O3 deleveraged dip": (o3, list(itertools.product((1.5, 2), (48, 72)))),
    "O4 funding vs trend": (o4, list(itertools.product((1.5, 2), (48, 72)))),
    "O5 flow + OI in trend": (o5, [(1,), (1.5,)]),
}
F3 = frame(f3((2, 48)))
f3_keys = F3.groupby("coin").t.apply(lambda s: np.sort(s.values.astype("datetime64[ns]")))


def overlap(f):
    hit = 0
    for r in f.itertuples():
        a = f3_keys.get(r.coin)
        if a is None:
            continue
        t = np.datetime64(r.t.tz_convert(None), "ns")
        i = np.searchsorted(a, t)
        hit += any(abs(t - a[j]) <= np.timedelta64(24, "h") for j in (i - 1, i) if 0 <= j < len(a))
    return hit / max(1, len(f))


res = {}
for name, (fn, grid) in FAMO.items():
    rows, best = [], None
    for p in grid:
        f = frame(fn(p))
        fi, te = f[f.t < FIT1], f[f.t >= FIT1]
        rows.append((len(te), te.ret.mean() if len(te) else np.nan))
        eqf, _ = book(fi, SLOTS)
        if best is None or eqf > best[0]:
            best = (eqf, p, f)
    eqf, p, f = best
    fi, te = f[f.t < FIT1], f[f.t >= FIT1]
    pf = te.ret[te.ret > 0].sum() / max(1e-9, -te.ret[te.ret < 0].sum()) if len(te) else 0
    yrs = {y: round(te[te.t.dt.year == y].ret.sum(), 1) for y in (2025, 2026)}
    eqt, ddt = book(te, SLOTS)
    pos = sum(1 for n_, a in rows if n_ and a > 0)
    ok = (len(te) >= 30 and te.ret.mean() > 0 and pf >= 1.2 and all(v > 0 for v in yrs.values())
          and len(fi) and fi.ret.mean() > 0 and eqt > 300 and pos >= len(grid) / 2)
    ov = overlap(te) if len(te) else 0
    lo, sh = te[te.ret.index.isin(te.index)], None
    res[name] = {"setting": p, "fit_n": len(fi), "fit_avg": round(fi.ret.mean(), 2) if len(fi) else None,
                 "fit_account": round(eqf), "test_n": len(te), "test_avg": round(te.ret.mean(), 2) if len(te) else None,
                 "test_pf": round(pf, 2), "test_years": yrs, "test_account": round(eqt), "test_drop_pct": round(ddt * 100),
                 "grid_positive_on_test": f"{pos}/{len(grid)}", "overlap_with_flowtrend": round(ov, 2), "pass": bool(ok)}
    print(f"{name:22} {str(p):10} fit n {len(fi):4} {(fi.ret.mean() if len(fi) else 0):+.2f}% acct {eqf:5.0f} | test n "
          f"{len(te):4} {(te.ret.mean() if len(te) else 0):+.2f}% PF {pf:4.2f} 2025 {yrs[2025]:+5.0f} 2026 {yrs[2026]:+5.0f} "
          f"acct {eqt:5.0f} drop {ddt*100:3.0f}% | grid+ {pos}/{len(grid)} | same as FlowTrend {ov*100:3.0f}% | "
          f"{'PASS' if ok else 'fail'}", flush=True)
(Path(__file__).parent / "batch_o_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
