"""Batch G (REGISTER_G_2026-10-13.md): more order-flow families + spot flow. Reuses flow_test.py / batch_b.py."""
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

src = (Path(__file__).parent / "flow_test.py").read_text(encoding="utf-8")
exec(src[:src.index("FAMF = {")])
SPOT = ROOT / "data" / "market" / "flow_spot"
SLOTS = 6

spot = []
for n in have:
    f = SPOT / f"{n}.feather"
    if not f.exists():
        continue
    q = pd.read_feather(f).drop_duplicates("date").set_index("date")
    D[n]["sqv"] = q["quote_volume"].reindex(D[n].index).fillna(0.0)
    D[n]["stbq"] = q["taker_buy_quote"].reindex(D[n].index).fillna(0.0)
    spot.append(n)
print(f"spot flow for {len(spot)} coins", flush=True)


def zcol(x, w, qv="qv", tb="tbq"):
    s = x[tb].rolling(w).sum() / x[qv].rolling(w).sum().replace(0, np.nan)
    return ((s - s.rolling(720, min_periods=500).mean()) / s.rolling(720, min_periods=500).std())


Z24 = {n: zcol(D[n], 24) for n in have}
R10 = {n: (np.log(D[n]["close"]) - np.log(D[n]["close"]).shift(240)) for n in have}
ZS = pd.DataFrame(Z24)
months = ZS.index.to_period("M").to_timestamp().tz_localize("UTC")
member = pd.DataFrame({n: [n in TOP.get(m, set()) for m in months] for n in ZS.columns}, index=ZS.index)
MKT = ZS.where(member).mean(axis=1)                        # mean z of the coins in that month's top-10


def g1(p):
    w, k, hold = p
    out = []
    for n in have:
        x = D[n]
        z = zcol(x, w).to_numpy()
        r = R10[n].to_numpy()
        run_events(n, x, (r > 0) & (z >= k), 1, hold, 2.5, out)
        run_events(n, x, (r < 0) & (z <= -k), -1, hold, 2.5, out)
    return out


def g2(p):
    k72, = p
    out = []
    for n in have:
        x = D[n]
        z, z72, r = Z24[n].to_numpy(), zcol(x, 72).to_numpy(), R10[n].to_numpy()
        run_events(n, x, (r > 0) & (z >= 2) & (z72 >= k72), 1, 48, 2, out)
        run_events(n, x, (r < 0) & (z <= -2) & (z72 <= -k72), -1, 48, 2, out)
    return out


def g3(p):
    k, hold = p
    out = []
    for n in ("BTC", "ETH"):
        x = D[n]
        m = MKT.reindex(x.index).to_numpy()
        run_events(n, x, m >= k, 1, hold, 2, out)
        run_events(n, x, m <= -k, -1, hold, 2, out)
    return out


def g4(p):
    k, = p
    out = []
    for n in have:
        x = D[n]
        rel = (Z24[n] - MKT.reindex(x.index)).to_numpy()
        r = R10[n].to_numpy()
        run_events(n, x, (r > 0) & (rel >= k), 1, 48, 2, out)
        run_events(n, x, (r < 0) & (rel <= -k), -1, 48, 2, out)
    return out


def fund_pct(x):
    st = x["fund"][x.index.hour % 8 == 0]
    return st.rolling(90, min_periods=60).rank(pct=True).reindex(x.index).ffill().to_numpy()


def g5(p):
    cut, = p
    out = []
    for n in have:
        x = D[n]
        z, r, fp = Z24[n].to_numpy(), R10[n].to_numpy(), fund_pct(x)
        run_events(n, x, (r > 0) & (z >= 2) & ~(fp >= 1 - cut), 1, 48, 2, out)
        run_events(n, x, (r < 0) & (z <= -2) & ~(fp <= cut), -1, 48, 2, out)
    return out


def g6(p):
    k, = p
    out = []
    for n in spot:
        x = D[n]
        zs, zp, r = zcol(x, 24, "sqv", "stbq").to_numpy(), Z24[n].to_numpy(), R10[n].to_numpy()
        run_events(n, x, (r > 0) & (zs >= k) & (zp < zs), 1, 48, 2, out)
        run_events(n, x, (r < 0) & (zs <= -k) & (zp > zs), -1, 48, 2, out)
    return out


def g7(p):
    k, = p
    out = []
    for n in spot:
        x = D[n]
        d = (zcol(x, 24, "sqv", "stbq") - Z24[n]).to_numpy()
        run_events(n, x, d >= k, 1, 48, 2, out)
        run_events(n, x, d <= -k, -1, 48, 2, out)
    return out


FAMG = {
    "G1 slow flow in trend": (g1, list(itertools.product((72, 168), (1.5, 2), (72, 120)))),
    "G2 sustained flow": (g2, [(1,), (1.5,)]),
    "G3 market flow majors": (g3, list(itertools.product((1, 1.5), (24, 48)))),
    "G4 own flow vs market": (g4, [(1.5,), (2,)]),
    "G5 flow no crowding": (g5, [(0.1,), (0.2,)]),
    "G6 spot-led buying": (g6, [(1.5,), (2,)]),
    "G7 spot vs perp": (g7, [(2,), (2.5,)]),
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
        near = [a[j] for j in (i - 1, i) if 0 <= j < len(a)]
        hit += any(abs(t - v) <= np.timedelta64(24, "h") for v in near)
    return hit / max(1, len(f))


res = {}
for name, (fn, grid) in FAMG.items():
    rows, best = [], None
    for p in grid:
        f = frame(fn(p))
        fi, te = f[f.t < FIT1], f[f.t >= FIT1]
        eqf, _ = book(fi, SLOTS)
        rows.append((p, len(te), te.ret.mean() if len(te) else np.nan))
        if best is None or eqf > best[0]:
            best = (eqf, p, f)
    eqf, p, f = best
    fi, te = f[f.t < FIT1], f[f.t >= FIT1]
    pf = te.ret[te.ret > 0].sum() / max(1e-9, -te.ret[te.ret < 0].sum()) if len(te) else 0
    yrs = {y: round(te[te.t.dt.year == y].ret.sum(), 1) for y in (2025, 2026)}
    eqt, ddt = book(te, SLOTS)
    pos = sum(1 for _, n_, a in rows if n_ and a > 0)
    ok = (len(te) >= 30 and te.ret.mean() > 0 and pf >= 1.2 and all(v > 0 for v in yrs.values())
          and len(fi) and fi.ret.mean() > 0 and eqt > 300)
    ov = overlap(te) if len(te) else 0
    res[name] = {"setting": p, "fit_n": len(fi), "fit_avg": round(fi.ret.mean(), 2) if len(fi) else None,
                 "fit_account": round(eqf), "test_n": len(te), "test_avg": round(te.ret.mean(), 2) if len(te) else None,
                 "test_pf": round(pf, 2), "test_years": yrs, "test_account": round(eqt),
                 "test_drop_pct": round(ddt * 100), "grid_positive_on_test": f"{pos}/{len(grid)}",
                 "overlap_with_flowtrend": round(ov, 2), "pass": bool(ok)}
    print(f"{name:22} {str(p):16} fit n {len(fi):4} {(fi.ret.mean() if len(fi) else 0):+.2f}% acct {eqf:5.0f} | test n "
          f"{len(te):4} {(te.ret.mean() if len(te) else 0):+.2f}% PF {pf:4.2f} 2025 {yrs[2025]:+5.0f} 2026 {yrs[2026]:+5.0f} "
          f"acct {eqt:5.0f} drop {ddt*100:3.0f}% | grid+ {pos}/{len(grid)} | same as FlowTrend {ov*100:3.0f}% | "
          f"{'PASS' if ok else 'fail'}", flush=True)
(Path(__file__).parent / "batch_g_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
