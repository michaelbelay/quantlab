"""Batch V (REGISTER_V_2026-10-13.md): Deribit DVOL signals on Binance BTC/ETH perps."""
import itertools
import json
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

src = (Path(__file__).parent / "batch_b.py").read_text(encoding="utf-8")
exec(src[:src.index("# ---------------------------------------------------------------- families")])
_b = src[src.index("def book("):src.index("res, chosen = {}, {}")]
exec(_b)
OUTD = ROOT / "data" / "market" / "dvol"
OUTD.mkdir(exist_ok=True)


def dvol(cur):
    f = OUTD / f"{cur}.csv"
    if f.exists():
        return pd.read_csv(f, index_col=0, parse_dates=True)["close"]
    rows, end = [], int(pd.Timestamp("2026-10-01", tz="UTC").timestamp() * 1000)
    start = int(pd.Timestamp("2021-01-01", tz="UTC").timestamp() * 1000)
    while end > start:
        u = (f"https://www.deribit.com/api/v2/public/get_volatility_index_data?currency={cur}"
             f"&start_timestamp={start}&end_timestamp={end}&resolution=1D")
        r = json.loads(urllib.request.urlopen(u, timeout=60).read())["result"]
        d = r["data"]
        if not d:
            break
        rows += d
        nxt = r.get("continuation")
        if not nxt or nxt >= end:
            break
        end = nxt
    s = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close"]).drop_duplicates("t")
    s.index = pd.to_datetime(s.t, unit="ms", utc=True)
    s = s.sort_index()[["close"]]
    s.to_csv(f)
    return s["close"]


DV = {c: dvol(c) for c in ("BTC", "ETH")}
for c, s in DV.items():
    print(f"DVOL {c}: {s.index[0].date()}..{s.index[-1].date()} n {len(s)}", flush=True)


def daily_feats(c):
    x = D[c]
    dc = x["close"].resample("1D").last()
    dv = DV[c].reindex(dc.index)
    rv = np.log(dc).diff().rolling(30).std() * np.sqrt(365) * 100
    vrp = dv - rv
    z = lambda s: (s - s.rolling(90, min_periods=60).mean()) / s.rolling(90, min_periods=60).std()
    r10 = np.log(dc) - np.log(dc).shift(10)
    return pd.DataFrame({"dv": dv, "zdv": z(dv), "zvrp": z(vrp), "r10": r10})


FE = {c: daily_feats(c) for c in ("BTC", "ETH")}


def trades(sig_fn, H):
    out = []
    for c in ("BTC", "ETH"):
        x, fe = D[c], FE[c]
        sg = sigma24(x)
        busy_until = pd.Timestamp("2000-01-01", tz="UTC")
        for day, d_ in sig_fn(fe):
            t = day + pd.Timedelta(days=1)                    # signal known at the close -> next day's 00:00 open
            if t <= busy_until or t not in x.index:
                continue
            i = hour_idx(x, t)
            if not np.isfinite(sg[i - 1]):
                continue
            e = x["open"].iat[i]
            r = sim(c, i, d_, H * 24, stop_px=e * (1 - d_ * 3 * sg[i - 1]))
            if r:
                busy_until = r[1]
                out.append((c, t, *r))
    f = pd.DataFrame(out, columns=["coin", "t", "t_in", "t_out", "ret"])
    f["ret"] *= 100
    return f[f.t >= FIT0]


def ev(mask, d_):
    return [(t, d_) for t in mask[mask.fillna(False)].index]


def v1(p):
    k, H = p
    return trades(lambda fe: ev(fe.zdv >= k, 1), H)


def v2(p):
    k, H = p
    return trades(lambda fe: sorted(ev(fe.zvrp >= k, 1) + ev(fe.zvrp <= -k, -1)), H)


def v3(p):
    H, = p
    return trades(lambda fe: ev((fe.zdv >= 1.5).rolling(5).max().astype(bool) & (fe.dv.diff(3) < 0), 1), H)


def v4(p):
    k, H = p
    return trades(lambda fe: ev((fe.zdv <= -k) & (fe.r10 < 0), -1), H)


FAMV = {"V1 panic buy": (v1, list(itertools.product((1.5, 2), (3, 7)))),
        "V2 variance premium": (v2, list(itertools.product((1, 1.5), (3, 7)))),
        "V3 fear fading": (v3, [(5,), (10,)]),
        "V4 complacency short": (v4, list(itertools.product((1.5, 2), (3, 7))))}
res = {}
for name, (fn, grid) in FAMV.items():
    best, rows = None, []
    for p in grid:
        f = fn(p)
        fi, te = f[f.t < FIT1], f[f.t >= FIT1]
        rows.append((len(te), te.ret.mean() if len(te) else np.nan))
        eq, _ = book(fi, 2)
        if best is None or eq > best[0]:
            best = (eq, p, f)
    eqf, p, f = best
    fi, te = f[f.t < FIT1], f[f.t >= FIT1]
    pf = te.ret[te.ret > 0].sum() / max(1e-9, -te.ret[te.ret < 0].sum()) if len(te) else 0
    yrs = {y: round(te[te.t.dt.year == y].ret.sum(), 1) for y in (2025, 2026)}
    eqt, ddt = book(te, 2)
    pos = sum(1 for n_, a in rows if n_ and a > 0)
    ok = (len(te) >= 20 and te.ret.mean() > 0 and pf >= 1.2 and all(v > 0 for v in yrs.values())
          and len(fi) and fi.ret.mean() > 0 and eqt > 300 and pos >= len(grid) / 2)
    res[name] = {"setting": p, "fit_n": len(fi), "fit_avg": round(fi.ret.mean(), 2) if len(fi) else None,
                 "fit_account": round(eqf), "test_n": len(te), "test_avg": round(te.ret.mean(), 2) if len(te) else None,
                 "test_pf": round(pf, 2), "test_years": yrs, "test_account": round(eqt), "test_drop_pct": round(ddt * 100),
                 "grid_positive_on_test": f"{pos}/{len(grid)}", "pass": bool(ok)}
    print(f"{name:22} {str(p):9} fit n {len(fi):3} {(fi.ret.mean() if len(fi) else 0):+.2f}% acct {eqf:5.0f} | test n "
          f"{len(te):3} {(te.ret.mean() if len(te) else 0):+.2f}% PF {pf:4.2f} 2025 {yrs[2025]:+5.0f} 2026 {yrs[2026]:+5.0f} "
          f"acct {eqt:5.0f} drop {ddt*100:3.0f}% | grid+ {pos}/{len(grid)} | {'PASS' if ok else 'fail'}", flush=True)
(Path(__file__).parent / "batch_v_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
