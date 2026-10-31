"""F3 flow-in-trend checks after it passed (2026-10-13): long/short split, years, coins, double cost, best days removed,
grid detail. Changes nothing."""
from pathlib import Path
import numpy as np, pandas as pd
src = (Path(__file__).parent / "flow_test.py").read_text(encoding="utf-8")
exec(src[:src.index("FAMF = {")])
for p in [(1, 24), (1, 48), (1.5, 24), (1.5, 48), (2, 24), (2, 48)]:
    f = frame(f3(p)); te = f[f.t >= FIT1]
    print(f"grid {p}: test n {len(te)} avg {te.ret.mean():+.2f}%  fit avg {f[f.t < FIT1].ret.mean():+.2f}%")
f = frame(f3((2, 48)))
f["side"] = np.where(f.t_out.notna(), 0, 0)
# side: re-derive from sim sign is not stored -> recompute by flags
longs = frame([r for r in f3((2, 48))])  # same rows; side split via a second pass below
L, S = [], []
for n in have:
    x = D[n]; z = share_z(x, 24); lc = np.log(x["close"]).to_numpy()
    r10 = lc - np.r_[np.full(240, np.nan), lc[:-240]]
    run_events(n, x, (r10 > 0) & (z >= 2), 1, 48, 2, L); run_events(n, x, (r10 < 0) & (z <= -2), -1, 48, 2, S)
L, S = frame(L), frame(S)
for lab, g in (("ALL", f), ("LONG", L), ("SHORT", S)):
    te, fi = g[g.t >= FIT1], g[g.t < FIT1]
    pf = te.ret[te.ret > 0].sum() / max(1e-9, -te.ret[te.ret < 0].sum())
    print(f"{lab:5} fit n {len(fi):4} {fi.ret.mean():+.2f}% | test n {len(te):4} {te.ret.mean():+.2f}% PF {pf:.2f} | per year:",
          {y: round(v, 0) for y, v in g.groupby(g.t.dt.year).ret.sum().items()})
te = f[f.t >= FIT1]
print("double cost (extra 0.2% per trade): test avg", round(te.ret.mean() - 0.2, 2), "fit avg", round(f[f.t < FIT1].ret.mean() - 0.2, 2))
day = te.groupby(te.t.dt.date).ret.sum().sort_values()
print("test sum", round(te.ret.sum()), " without best 5 days", round(day.iloc[:-5].sum()), " without best 10", round(day.iloc[:-10].sum()))
c = te.groupby("coin").ret.agg(["count", "sum"]).sort_values("sum")
print("coins positive", (c["sum"] > 0).sum(), "/", len(c), " top 3:", c.tail(3)["sum"].round(0).to_dict(), " without top 3 coins:", round(c["sum"].iloc[:-3].sum()))
for lev in (1, 2):
    for lab, g in (("fit 2022-24", f[f.t < FIT1]), ("test 2025-26", te), ("2022-2026 all", f)):
        eq, dd = book(g) if lev == 1 else (lambda r: r)(book(g.assign(ret=g.ret * 2)))
        print(f"  {lev}x {lab:14} 300 -> {eq:6.0f}  drop {dd*100:3.0f}%")
