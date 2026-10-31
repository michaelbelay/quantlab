"""Fresh strategy search S1-S8 (REGISTER_2026-10-13.md). Writes fresh_results.json, prints the table.

    .venv\\Scripts\\python.exe research\\fresh\\fresh_ideas.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
FUT = ROOT / "data" / "market" / "dev_1h" / "binance" / "futures"
COINS = ["BTC", "ETH", "BNB", "SOL", "XRP"]
SIDE = 0.001                                   # cost per side
FIT_END = pd.Timestamp("2024-01-01", tz="UTC")


def load(c: str) -> pd.DataFrame:
    d = pd.read_feather(FUT / f"{c}_USDT_USDT-1h-futures.feather")
    d["date"] = pd.to_datetime(d["date"], utc=True)
    d = d.set_index("date").asfreq("1h").ffill()
    f = pd.read_feather(FUT / f"{c}_USDT_USDT-1h-funding_rate.feather")
    f["date"] = pd.to_datetime(f["date"], utc=True)
    d["fund"] = f.set_index("date")["funding_rate"].reindex(d.index).fillna(0.0)
    return d


D = {c: load(c) for c in COINS}
IDX = D["BTC"].index


def trade(c: str, i: int, j: int, d: int, stop: float | None = None, tgt: float | None = None, legs: int = 1) -> float:
    """Enter at open of bar i, last bar j-1 (exit at its close). stop/tgt = fractions; stop first in a bar.
    Returns net fraction after costs and funding."""
    x = D[c]
    j = min(j, len(x))
    e = x["open"].iat[i]
    hi, lo, cl = x["high"].to_numpy()[i:j], x["low"].to_numpy()[i:j], x["close"].to_numpy()[i:j]
    g, k_end = d * (cl[-1] / e - 1), j
    for k in range(len(cl)):
        fav = (hi[k] / e - 1) if d == 1 else (1 - lo[k] / e)
        adv = (1 - lo[k] / e) if d == 1 else (hi[k] / e - 1)
        if stop is not None and adv >= stop:
            g, k_end = -stop, i + k + 1
            break
        if tgt is not None and fav >= tgt:
            g, k_end = tgt, i + k + 1
            break
    fund = x["fund"].to_numpy()[i + 1:k_end + 1].sum()      # funding stamped at bar open, paid while held
    return g - 2 * SIDE - d * fund


def rows(name: str, out: list) -> pd.DataFrame:
    return pd.DataFrame(out, columns=["t", "ret"]).assign(idea=name)


def fit_mask(t: pd.DatetimeIndex) -> np.ndarray:
    return np.asarray(t < FIT_END)


R = []
b = D["BTC"]
r1 = np.log(b["close"] / b["open"])

# S1 hour of day
fit = r1[fit_mask(r1.index)]
g = fit.groupby(fit.index.hour)
t = g.mean() / g.std() * np.sqrt(g.count())
sel = {h: int(np.sign(t[h])) for h in t.index if abs(t[h]) > 2}
out = []
if sel:
    hrs = b.index.hour.to_numpy()
    i, n = 0, len(b)
    while i < n:
        h = hrs[i]
        if h in sel:
            d, j = sel[h], i
            while j < n and hrs[j] in sel and sel[hrs[j]] == d:
                j += 1
            out.append((b.index[i], trade("BTC", i, j, d)))
            i = j
        else:
            i += 1
R.append(rows("S1 hour of day", out))
s1_note = {str(h): v for h, v in sel.items()}

# S2 weekend (Fri 20:00 -> Mon 00:00)
starts = np.flatnonzero((b.index.dayofweek == 4) & (b.index.hour == 20))
wk = [(b.index[i], trade("BTC", i, i + 52, 1) + 2 * SIDE) for i in starts if i + 52 <= len(b)]   # gross long, sign later
fitw = np.mean([r for tt, r in wk if tt < FIT_END])
dw = 1 if fitw > 0 else -1
R.append(rows("S2 weekend", [(tt, trade("BTC", i, i + 52, dw)) for (tt, _), i in zip(wk, starts)]))

# S3 day of week
dr = np.log(b["close"].resample("1D").last() / b["open"].resample("1D").first())
f = dr[dr.index < FIT_END]
gd = f.groupby(f.index.dayofweek)
td = gd.mean() / gd.std() * np.sqrt(gd.count())
best = td.abs().idxmax()
out = []
if abs(td[best]) > 2:
    dd = int(np.sign(td[best]))
    for i in np.flatnonzero((b.index.dayofweek == best) & (b.index.hour == 0)):
        if i + 24 <= len(b):
            out.append((b.index[i], trade("BTC", i, i + 24, dd)))
R.append(rows("S3 day of week", out))

# S4 CME gap
out = []
for i in np.flatnonzero((b.index.dayofweek == 6) & (b.index.hour == 23)):
    fc = b["close"].iat[i - 51] if i >= 51 else np.nan                 # Fri 20:00 bar close = 21:00
    o = b["open"].iat[i]
    gap = o / fc - 1
    if np.isfinite(gap) and abs(gap) > 0.01 and i + 72 <= len(b):
        d = -1 if gap > 0 else 1
        out.append((b.index[i], trade("BTC", i, i + 72, d, stop=abs(gap), tgt=abs(gap))))
R.append(rows("S4 CME gap", out))

# S5 ETH/BTC spread
lr = np.log(D["ETH"]["close"] / b["close"])
z = (lr - lr.rolling(168).mean()) / lr.rolling(168).std()
zz, out, i = z.to_numpy(), [], 200
while i < len(b) - 73:
    if np.isfinite(zz[i]) and abs(zz[i]) > 2.5:
        de = -1 if zz[i] > 0 else 1                                     # ETH rich -> short ETH, long BTC
        j = i + 1
        while j < i + 1 + 72 and np.isfinite(zz[j]) and np.sign(zz[j]) == np.sign(zz[i]):
            j += 1
        ret = (trade("ETH", i + 1, j + 1, de) + trade("BTC", i + 1, j + 1, -de)) / 2
        out.append((b.index[i], ret))
        i = j + 1
    else:
        i += 1
R.append(rows("S5 ETH/BTC spread", out))

# S6 turn of month
out = []
days = b.index.normalize()
last_day = (b.index + pd.Timedelta(days=1)).month != b.index.month
for i in np.flatnonzero(last_day & (b.index.hour == 0)):
    if i + 96 <= len(b):
        out.append((b.index[i], trade("BTC", i, i + 96, 1)))
R.append(rows("S6 turn of month", out))

# S7 dip in uptrend
out = []
for c in COINS:
    x = D[c]
    lc = np.log(x["close"])
    sig = lc.diff().rolling(720, min_periods=500).std() * np.sqrt(24)
    r24, r20d = lc - lc.shift(24), x["close"] / x["close"].shift(480) - 1
    cond = ((r20d > 0) & (r24 <= -2 * sig)).to_numpy()
    last = -10**9
    for i in np.flatnonzero(cond):
        if i - last >= 24 and i + 1 + 72 <= len(x):
            out.append((x.index[i], trade(c, i + 1, i + 73, 1, stop=2 * sig.iat[i])))
            last = i
R.append(rows("S7 dip in uptrend", out))

# S8 BTC leads
out = []
br = (b["close"] / b["open"] - 1).to_numpy()
for i in np.flatnonzero(np.abs(br) >= 0.015):
    d = int(np.sign(br[i]))
    for c in COINS[1:]:
        x = D[c]
        cr = x["close"].iat[i] / x["open"].iat[i] - 1
        if d * cr < 0.5 * abs(br[i]) and i + 4 <= len(x):
            out.append((b.index[i], trade(c, i + 1, i + 4, d)))
R.append(rows("S8 BTC leads", out))

# ------------------------------------------------------------------ verdicts
res = {}
print(f"{'idea':22} {'FIT n':>6} {'FIT avg':>8} | {'TEST n':>6} {'avg':>7} {'PF':>5}  2024  2025  2026 | verdict")
for name, g in pd.concat(R).groupby("idea", sort=False):
    g = g.assign(ret=g.ret.astype(float) * 100, t=pd.to_datetime(g.t, utc=True))
    fi, te = g[g.t < FIT_END], g[g.t >= FIT_END]
    pf = te.ret[te.ret > 0].sum() / max(1e-9, -te.ret[te.ret < 0].sum()) if len(te) else 0
    yrs = {y: round(te[te.t.dt.year == y].ret.sum(), 1) for y in (2024, 2025, 2026)}
    ok = (len(te) >= 30 and te.ret.mean() > 0 and pf >= 1.2 and sum(v > 0 for v in yrs.values()) >= 2
          and len(fi) and fi.ret.mean() > 0)
    res[name] = {"fit_n": len(fi), "fit_avg": round(fi.ret.mean(), 3) if len(fi) else None,
                 "test_n": len(te), "test_avg": round(te.ret.mean(), 3) if len(te) else None,
                 "test_pf": round(pf, 2), "test_years_sum_pct": yrs, "pass": bool(ok)}
    print(f"{name:22} {len(fi):6} {res[name]['fit_avg'] or 0:+8.3f} | {len(te):6} {res[name]['test_avg'] or 0:+7.3f} "
          f"{pf:5.2f} {yrs[2024]:+5.0f} {yrs[2025]:+5.0f} {yrs[2026]:+5.0f} | {'PASS' if ok else 'fail'}")
res["_notes"] = {"S1_hours_fit": s1_note, "S2_side": dw, "S3_day_t": {int(k): round(v, 2) for k, v in td.items()}}
(HERE / "fresh_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
print(res["_notes"])
