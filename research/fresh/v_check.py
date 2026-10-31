"""Checks for V2 / V4 (batch V passes): years, coins, sides, double cost, top trades removed, neighbours."""
import itertools
from pathlib import Path
import numpy as np, pandas as pd
src = (Path(__file__).parent / "batch_v.py").read_text(encoding="utf-8")
exec(src[:src.index("FAMV = {")])
def rep(lab, f):
    te = f[f.t >= FIT1]
    def s(g): return f"n {len(g):3} {g.ret.mean() if len(g) else 0:+.2f}%"
    print(f"\n{lab}: all {s(f)} | test {s(te)}")
    print("  years :", {int(y): f"{g.ret.sum():+.0f} ({len(g)})" for y, g in f.groupby(f.t.dt.year)})
    print("  coins :", {c: s(g) for c, g in f.groupby("coin")}, " test coins:", {c: s(g) for c, g in te.groupby("coin")})
    if "side" in f: print("  sides :", {d: s(g) for d, g in f.groupby("side")}, " test:", {d: s(g) for d, g in te.groupby("side")})
    print(f"  double cost test avg {te.ret.mean() - 0.2:+.2f}% | test without best 3: {te.ret.sort_values().iloc[:-3].mean():+.2f}% "
          f"| all without best 5: {f.ret.sort_values().iloc[:-5].sum():+.0f} of {f.ret.sum():+.0f}")
    print(f"  account all 2022-26 (2 slots): {book(f, 2)[0]:.0f} drop {book(f, 2)[1]*100:.0f}%")
def side(f):
    f = f.copy(); f["side"] = np.where(f.t_out > f.t_in, 0, 0); return f
f2 = v2((1.5, 7)); f4 = v4((1.5, 7))
rep("V2 (1.5, 7)", f2); rep("V4 (1.5, 7)", f4)
# V2 sides: rerun each side alone
lo = trades(lambda fe: ev(fe.zvrp >= 1.5, 1), 7); sh = trades(lambda fe: ev(fe.zvrp <= -1.5, -1), 7)
for lab, g in (("V2 long side", lo), ("V2 short side", sh)):
    te = g[g.t >= FIT1]
    print(f"{lab}: all n {len(g)} {g.ret.mean():+.2f}% | test n {len(te)} {te.ret.mean():+.2f}% | years",
          {int(y): round(h.ret.sum()) for y, h in g.groupby(g.t.dt.year)})
print("\nneighbours (test avg / test n / fit avg):")
for k, H in itertools.product((1.0, 1.25, 1.5, 1.75, 2.0, 2.5), (3, 5, 7, 10)):
    a = v4((k, H)); b = v2((k, H))
    ta, tb, fa, fb = a[a.t >= FIT1], b[b.t >= FIT1], a[a.t < FIT1], b[b.t < FIT1]
    print(f"  k {k:4} H {H:2} | V4 test {ta.ret.mean():+.2f}% n {len(ta):3} fit {fa.ret.mean():+.2f}% | "
          f"V2 test {tb.ret.mean():+.2f}% n {len(tb):3} fit {fb.ret.mean():+.2f}%")
ov = len(set(zip(f4.coin, f4.t)) & set(zip(sh.coin, sh.t)))
print(f"\nV4 trades that are also V2 shorts: {ov}/{len(f4)}")
