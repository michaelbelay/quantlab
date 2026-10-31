"""Batch H (REGISTER_H_2026-10-13.md): Bear-Rip Short v2 - failed-rally confirmation + stop-distance sizing at 5x.

    .venv\\Scripts\\python.exe research\\fresh\\bear_rip.py
"""
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

src = (Path(__file__).parent / "batch_b.py").read_text(encoding="utf-8")
exec(src[:src.index("# ---------------------------------------------------------------- families")])

LEV, MMR, MAXPOS = 5.0, 0.01, 2
btc = D["BTC"]["close"]
BEAR = ((btc / btc.shift(480) - 1 < 0) & (btc < btc.rolling(1200, min_periods=1000).mean()))


def setups(n, k, tr):
    x = D[n]
    lc = np.log(x["close"]).to_numpy()
    sg = sigma24(x)
    r24 = lc - np.r_[np.full(24, np.nan), lc[:-24]]
    rtr = lc - np.r_[np.full(tr * 24, np.nan), lc[:-tr * 24]]
    bear = BEAR.reindex(x.index).fillna(False).to_numpy()
    return np.flatnonzero((rtr < 0) & (r24 >= k * sg) & bear), sg


def h0(p):
    k, tr, hold = p
    out = []
    for n in USE:
        x = D[n]
        idx, sg = setups(n, k, tr)
        last = -10**9
        for i in idx:
            if i - last < 24 or i + 2 > len(x) or not in_top(n, x.index[i]):
                continue
            last = i
            e = x["open"].iat[i + 1]
            r = sim(n, i + 1, -1, hold, stop_px=e * (1 + 3 * sg[i]))
            if r:
                out.append((n, x.index[i], *r, 3 * sg[i]))
    return out


def h1(p):
    k, tr, c, hold = p
    out = []
    for n in USE:
        x = D[n]
        h, cl, o = x["high"].to_numpy(), x["close"].to_numpy(), x["open"].to_numpy()
        idx, sg = setups(n, k, tr)
        last = -10**9
        for i in idx:
            if i - last < 24 or i + 26 > len(x) or not in_top(n, x.index[i]):
                continue
            last = i
            peak = h[i]
            for j in range(i + 1, i + 25):
                peak = max(peak, h[j])
                if cl[j] <= peak * (1 - c * sg[i]):
                    e = o[j + 1]
                    stop = peak * (1 + 0.5 * sg[i])
                    r = sim(n, j + 1, -1, hold, stop_px=stop)
                    if r and stop > e:
                        out.append((n, x.index[i], *r, stop / e - 1))
                    break
    return out


def frame(rows):
    f = pd.DataFrame(rows, columns=["coin", "t", "t_in", "t_out", "ret", "sd"])
    f["ret"] = np.maximum(f["ret"], -(1 / LEV))          # isolated: never lose more than the margin
    return f[f.t >= FIT0]


def book(f, risk=0.01, start=300.0):
    f = f.sort_values("t_in")
    taken, skipped = [], 0
    for r in f.itertuples():
        if sum(1 for t_o, _ in taken if t_o > r.t_in) >= MAXPOS:
            continue
        if r.sd >= 1 / LEV - MMR - 0.01:
            skipped += 1
            continue
        eq = start + sum(p for t_o, p in taken if t_o <= r.t_in)
        notional = min(risk * eq / r.sd, LEV * eq / MAXPOS)
        if notional < 5:
            skipped += 1
            continue
        taken.append((r.t_out, notional * r.ret))
    if not taken:
        return start, 0.0, 0, skipped
    c = pd.Series([p for _, p in taken], index=[t for t, _ in taken]).sort_index().cumsum() + start
    return float(c.iloc[-1]), float((1 - c / c.cummax().clip(lower=start)).max()), len(taken), skipped


def run(name, fn, grid):
    best, rows = None, []
    for p in grid:
        f = frame(fn(p))
        fi, te = f[f.t < FIT1], f[f.t >= FIT1]
        rows.append((p, len(te), te.ret.mean() if len(te) else np.nan))
        eq = book(fi)[0]
        if best is None or eq > best[0]:
            best = (eq, p, f)
    _, p, f = best
    fi, te = f[f.t < FIT1], f[f.t >= FIT1]
    pf = te.ret[te.ret > 0].sum() / max(1e-9, -te.ret[te.ret < 0].sum()) if len(te) else 0
    ef, df_, nf, _ = book(fi)
    et, dt, nt, sk = book(te)
    et2, dt2, _, _ = book(te, 0.02)
    pos = sum(1 for _, n_, a in rows if n_ and a > 0)
    yrs = {int(y): round(g.ret.sum() * 100, 1) for y, g in f.groupby(f.t.dt.year)}
    r = {"setting": p, "fit_n": len(fi), "fit_avg_pct": round(fi.ret.mean() * 100, 2) if len(fi) else None,
         "fit_account": round(ef), "fit_drop_pct": round(df_ * 100), "test_n": len(te),
         "test_avg_pct": round(te.ret.mean() * 100, 2) if len(te) else None, "test_pf": round(pf, 2),
         "test_account_1pct": round(et, 1), "test_drop_pct": round(dt * 100, 1), "test_trades_taken": nt,
         "test_skipped": sk, "test_account_2pct": round(et2, 1), "test_drop_2pct": round(dt2 * 100, 1),
         "median_stop_pct": round(te.sd.median() * 100, 1) if len(te) else None,
         "grid_positive_on_test": f"{pos}/{len(grid)}", "years_sum_pct": yrs}
    print(f"{name:22} {str(p):20} fit n {len(fi):3} {r['fit_avg_pct'] or 0:+.2f}% acct {ef:5.0f} | test n {len(te):3} "
          f"{r['test_avg_pct'] or 0:+.2f}% PF {pf:4.2f} acct1% {et:6.1f} drop {dt*100:4.1f}% acct2% {et2:6.1f} drop "
          f"{dt2*100:4.1f}% | stop {r['median_stop_pct']}% | grid+ {pos}/{len(grid)} | {yrs}", flush=True)
    return r, te


print(f"bear hours 2022-01..2026-09: {BEAR[BEAR.index >= FIT0].mean()*100:.0f}% "
      f"(fit {BEAR[(BEAR.index >= FIT0) & (BEAR.index < FIT1)].mean()*100:.0f}%, test {BEAR[BEAR.index >= FIT1].mean()*100:.0f}%)")
r0, te0 = run("H0 B3 bear-gated", h0, list(itertools.product((1.5, 2.0, 2.5), (10, 20), (48, 72))))
r1, te1 = run("H1 Bear-Rip v2", h1, list(itertools.product((1.5, 2.0, 2.5), (10, 20), (0.5, 1.0), (48, 72))))
pf1 = r1["test_pf"]
ok = (r1["test_n"] >= 30 and (r1["test_avg_pct"] or 0) > 0 and pf1 >= 1.2 and r1["test_account_1pct"] > 300
      and r1["test_drop_pct"] <= 15 and (r1["fit_avg_pct"] or 0) > 0
      and int(r1["grid_positive_on_test"].split("/")[0]) >= 12 and r1["test_account_1pct"] > r0["test_account_1pct"])
r1["pass"] = bool(ok)
print("H1 PASS" if ok else "H1 fail")
(Path(__file__).parent / "bear_rip_results.json").write_text(json.dumps({"H0": r0, "H1": r1}, indent=1, default=str),
                                                             encoding="utf-8")
