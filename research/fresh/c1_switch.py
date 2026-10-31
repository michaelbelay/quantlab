"""C1: rip-short in bear (BTC 20d < 0) + dip-long in bull (BTC 20d > 0). Registered in REGISTER_B."""
from pathlib import Path
import numpy as np, pandas as pd
src = (Path(__file__).parent / "batch_b.py").read_text(encoding="utf-8")
exec(src[:src.index("res, chosen = {}, {}")])
btc = D["BTC"]["close"]
b20 = btc / btc.shift(480) - 1
def gate(f, bear):
    v = b20.reindex(f.t).to_numpy()
    return f[(v < 0) if bear else (v > 0)]
def pick(fn, grid, bear):
    best = None
    for p in grid:
        f = gate(frame(fn(p)), bear)
        eq, _ = book(f[f.t < FIT1])
        if best is None or eq > best[0]:
            best = (eq, p, f)
    return best
def show(lab, f):
    fi, te = f[f.t < FIT1], f[f.t >= FIT1]
    pf = te.ret[te.ret > 0].sum() / max(1e-9, -te.ret[te.ret < 0].sum())
    ef, df_ = book(fi); et, dt = book(te)
    ys = " ".join(f"{y} {g.ret.sum():+5.0f}" for y, g in f.groupby(f.t.dt.year))
    print(f"{lab:28} fit n {len(fi):4} {fi.ret.mean():+.2f}% acct {ef:5.0f} drop {df_*100:3.0f}% | test n {len(te):4} "
          f"{te.ret.mean():+.2f}% PF {pf:4.2f} acct {et:5.0f} drop {dt*100:3.0f}% | {ys}", flush=True)
    return te, pf
eqr, pr, fr = pick(FAM["B3 rip in downtrend"][0], FAM["B3 rip in downtrend"][1], True)
eqd, pd_, fd = pick(FAM["B0 dip in uptrend"][0], FAM["B0 dip in uptrend"][1], False)
print("chosen on 2022-2024: rip-short", pr, " dip-long", pd_)
show("rip short, bear only", fr)
show("dip long, bull only", fd)
te, pf = show("C1 both, one account", pd.concat([fr, fd]))
yrs = {y: te[te.t.dt.year == y].ret.sum() for y in (2025, 2026)}
print("C1 pass:", len(te) >= 30 and te.ret.mean() > 0 and pf >= 1.2 and all(v > 0 for v in yrs.values()) and book(te)[0] > 300)
