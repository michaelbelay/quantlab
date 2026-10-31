"""Batch R (REGISTER_R_2026-10-13.md): FlowTrend rule, unchanged, on point-in-time ranks 11-30 (+ ranks 1-30 book)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

src = (Path(__file__).parent / "batch_b.py").read_text(encoding="utf-8")
exec(src[:src.index("# ---------------------------------------------------------------- families")])
FLOW = ROOT / "data" / "market" / "flow"
RANK = {m: list(V.shift(1).loc[m].dropna().nlargest(30).index) for m in V.index[1:]}
ALL30 = sorted(set().union(*[set(v) for m, v in RANK.items() if m >= pd.Timestamp("2021-12-01", tz="UTC")]))
for n in ALL30:
    if n not in D:
        D[n] = load(n)
have = []
for n in ALL30:
    f = FLOW / f"{n}.feather"
    if D.get(n) is None or not f.exists():
        continue
    q = pd.read_feather(f).drop_duplicates("date").set_index("date")
    D[n]["qv"] = q["quote_volume"].reindex(D[n].index).fillna(0.0)
    D[n]["tbq"] = q["taker_buy_quote"].reindex(D[n].index).fillna(0.0)
    have.append(n)
print(f"{len(have)}/{len(ALL30)} top-30 coins with flow", flush=True)


def tier(n, t):
    r = RANK.get(pd.Timestamp(t.year, t.month, 1, tz="UTC"), [])
    return (r.index(n) + 1) if n in r else 99


def signals():
    out = []
    for n in have:
        x = D[n]
        s = x["tbq"].rolling(24).sum() / x["qv"].rolling(24).sum().replace(0, np.nan)
        z = ((s - s.rolling(720, min_periods=500).mean()) / s.rolling(720, min_periods=500).std()).to_numpy()
        lc = np.log(x["close"]).to_numpy()
        r10 = lc - np.r_[np.full(240, np.nan), lc[:-240]]
        sg = sigma24(x)
        for d_, cond in ((1, (r10 > 0) & (z >= 2)), (-1, (r10 < 0) & (z <= -2))):
            last = -10**9
            for i in np.flatnonzero(cond):
                if i - last < 24 or i + 2 > len(x) or not np.isfinite(sg[i]):
                    continue
                rk = tier(n, x.index[i])
                if rk > 30:
                    continue
                last = i
                e = x["open"].iat[i + 1]
                r = sim(n, i + 1, d_, 48, stop_px=e * (1 - d_ * 2 * sg[i]))
                if r:
                    out.append((n, x.index[i], *r, rk))
    f = pd.DataFrame(out, columns=["coin", "t", "t_in", "t_out", "ret", "rank"])
    f["ret"] *= 100
    return f[f.t >= FIT0]


def book(f, slots=6, start=300.0):
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


F = signals()
res = {}
for lab, sel in (("R0 ranks 1-10 (FlowTrend)", F["rank"] <= 10), ("R1 ranks 11-30", F["rank"] > 10),
                 ("R2 ranks 1-30 one book", F["rank"] <= 30)):
    f = F[sel]
    row = {}
    for per, g in (("2022-24", f[f.t < FIT1]), ("2025-26", f[f.t >= FIT1])):
        pf = g.ret[g.ret > 0].sum() / max(1e-9, -g.ret[g.ret < 0].sum())
        eq, dd = book(g)
        yrs = {int(y): round(h.ret.sum(), 1) for y, h in g.groupby(g.t.dt.year)}
        row[per] = {"n": len(g), "avg": round(g.ret.mean(), 3), "pf": round(pf, 2), "account": round(eq),
                    "drop_pct": round(dd * 100), "years": yrs}
        print(f"{lab:26} {per}: n {len(g):4} {g.ret.mean():+.2f}% PF {pf:4.2f} acct {eq:6.0f} drop {dd*100:3.0f}% {yrs}",
              flush=True)
    res[lab] = row
m = res["R1 ranks 11-30"]
ok = all(m[p]["n"] >= 30 and m[p]["avg"] > 0 and m[p]["pf"] >= 1.2 and m[p]["account"] > 300 for p in m) \
    and m["2025-26"]["years"].get(2025, 0) > 0 and m["2025-26"]["years"].get(2026, 0) > 0
res["R1 pass"] = bool(ok)
print("R1", "PASS" if ok else "fail")
(Path(__file__).parent / "batch_r_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
