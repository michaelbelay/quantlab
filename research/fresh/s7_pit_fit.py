"""S7 on the point-in-time top-10: choose settings on FIT (2021-2023) only, then report TEST and the 300 account."""
import itertools, sys, io, contextlib
from pathlib import Path
import pandas as pd
sys.argv = ["x"]
src = (Path(__file__).parent / "s7_check.py").read_text(encoding="utf-8")
head = src[:src.index('COINS = ["BTC"')]
book_src = src[src.index('def book('):src.index('print("' + chr(92) + 'n4.')]
exec(head); exec(book_src)
names = sorted({p.name.split("_")[0] for p in FUT.glob("*_USDT_USDT-1h-futures.feather")} - STABLE)
D, val = {}, {}
for n in names:
    x = load(n)
    if x is not None:
        val[n] = (x["close"] * x["volume"]).resample("MS").sum(); D[n] = x
V = pd.DataFrame(val)
top = {m: set(V.shift(1).loc[m].dropna().nlargest(10).index) for m in V.index[1:]}
use = sorted(set().union(*top.values()))
D = {n: D[n] for n in use}
res = []
for dip, hold, stop, tr in itertools.product((1.5, 2.0, 2.5), (48, 72, 96), (1.5, 2.0, 3.0), (10, 20, 40)):
    rows = []
    for n in use:
        for s in signals(D[n], dip, hold, stop, tr):
            if n in top.get(pd.Timestamp(s[0].year, s[0].month, 1, tz="UTC"), set()):
                rows.append((n, *s))
    f = frame(rows)
    fi = f[f.t < FIT_END]
    eq_fit, dd_fit, _ = book(fi, 1)
    res.append((dip, hold, stop, tr, fi.ret.mean(), eq_fit, dd_fit, f))
best = max(res, key=lambda r: r[5])                       # best 300-account end value on FIT only
dip, hold, stop, tr, fa, ef, df_, f = best
print(f"chosen on 2021-2023 only: dip {dip} sigma, hold {hold}h, stop {stop} sigma, trend {tr}d  (fit account 300 -> {ef:.0f}, drop {df_*100:.0f}%)")
print("   ", summary(f))
for lev in (1, 2):
    te = f[f.t >= FIT_END]
    eq, dd, yr = book(te, lev)
    print(f"   TEST 2024-01..2026-09 alone, {lev}x: 300 -> {eq:.0f}, max drop {dd*100:.0f}%, year-end {yr}")
print(f"   FIT-positive settings: {sum(r[5] > 300 for r in res)}/81")
