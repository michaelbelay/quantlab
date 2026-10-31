"""Batch P (REGISTER_P_2026-10-13.md). Reuses batch_o.py (OI) / flow_test.py / batch_b.py."""
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

src = (Path(__file__).parent / "batch_o.py").read_text(encoding="utf-8")
exec(src[:src.index("FAMO = {")])


def p1(p):
    k, h = p
    return fam(lambda q: ((np.abs(q["r10"]) <= 1.5 * q["sg"]) & (q["r24"] <= -k * q["sg"]),
                          (np.abs(q["r10"]) <= 1.5 * q["sg"]) & (q["r24"] >= k * q["sg"])), h, 3)


def p2(p):
    k, h = p
    out = []
    for n in oi_have:
        x, q = D[n], PRE[n]
        c = x["close"]
        hi, lo = (c >= c.rolling(480).max()).to_numpy(), (c <= c.rolling(480).min()).to_numpy()
        run_events(n, x, hi & (q["zoi"] >= k), 1, h, 3, out)
        run_events(n, x, lo & (q["zoi"] >= k), -1, h, 3, out)
    return out


def p3(p):
    hold_d, = p
    out = []
    btc = D["BTC"]["close"]
    months = sorted(TOP)
    for a, b in zip(months, months[1:]):
        if b < pd.Timestamp("2022-01-01", tz="UTC") or b > pd.Timestamp("2026-09-01", tz="UTC"):
            continue
        up = btc.asof(b - pd.Timedelta(hours=1)) > btc.asof(b - pd.Timedelta(days=20))
        for n, d_ in [(n, 1) for n in TOP[b] - TOP[a] if up] + [(n, -1) for n in TOP[a] - TOP[b] if not up]:
            if n not in D or b not in D[n].index:
                continue
            x = D[n]
            i = hour_idx(x, b)
            sg = sigma24(x)[i - 1]
            if not np.isfinite(sg):
                continue
            e = x["open"].iat[i]
            r = sim(n, i, d_, hold_d * 24, stop_px=e * (1 - d_ * 3 * sg))
            if r:
                out.append((n, b, *r))
    return out


def p4(p):
    k, h = p
    out = []
    for n in oi_have:
        x, q = D[n], PRE[n]
        c = x["close"]
        ma = c.rolling(480).mean()
        r20 = (np.log(c) - np.log(c).shift(480)).to_numpy()
        below, above = (c < ma), (c > ma)
        xdn = (below & above.shift(1, fill_value=False)).to_numpy()
        xup = (above & below.shift(1, fill_value=False)).to_numpy()
        fd = pd.Series(xdn).rolling(72).sum().to_numpy() == 1
        fu = pd.Series(xup).rolling(72).sum().to_numpy() == 1
        run_events(n, x, (r20 > 0) & xdn & fd & (q["zflow"] >= k), 1, h, 3, out)
        run_events(n, x, (r20 < 0) & xup & fu & (q["zflow"] <= -k), -1, h, 3, out)
    return out


def p5(p):
    m, = p
    out = []
    for n in oi_have:
        x, q = D[n], PRE[n]
        o, hi, lo, cl = (x[c].to_numpy() for c in ("open", "high", "low", "close"))
        idx = x.index
        starts = np.flatnonzero((idx.hour == 0))
        for s in starts:
            if s + 24 >= len(x) or not in_top(n, idx[s]) or not np.isfinite(q["sg"][s]):
                continue
            rh, rl = hi[s:s + 4].max(), lo[s:s + 4].min()
            if (rh - rl) / o[s] < m * q["sg"][s] or not np.isfinite(q["r10"][s + 3]):
                continue
            d_ = 1 if q["r10"][s + 3] > 0 else -1
            for j in range(s + 4, s + 23):
                if (d_ == 1 and cl[j] > rh) or (d_ == -1 and cl[j] < rl):
                    r = sim(n, j + 1, d_, s + 24 - (j + 1), stop_px=rl if d_ == 1 else rh)
                    if r:
                        out.append((n, idx[j], *r))
                    break
    return out


FAMP = {
    "P1 spike fade flat": (p1, list(itertools.product((2, 2.5, 3), (24, 48)))),
    "P2 breakout + OI": (p2, list(itertools.product((1, 1.5), (72, 120)))),
    "P3 top-10 newcomer": (p3, [(7,), (14,)]),
    "P4 pullback + buyers": (p4, list(itertools.product((0.5, 1), (72, 120)))),
    "P5 day-range breakout": (p5, [(0,), (0.5,)]),
}
FAMO = FAMP
src = (Path(__file__).parent / "batch_o.py").read_text(encoding="utf-8")
src_o = src[src.index("F3 = frame("):].replace("batch_o_results.json", "batch_p_results.json")
exec(src_o)
