"""Batch L (REGISTER_L_2026-10-13.md): BTC -> alt lead-lag on 1-second futures prices.

    .venv\\Scripts\\python.exe research\\fresh\\leadlag.py
"""
import itertools
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
TD = ROOT / "data" / "market" / "ticks"
FOL = ["ETH", "SOL", "XRP", "DOGE", "BNB"]
days = sorted(p.stem for p in (TD / "BTC").glob("*.npy"))
ND, S = len(days), 86400
P = {c: np.concatenate([np.load(TD / c / f"{d}.npy").astype(np.float32) for d in days]) for c in ["BTC", *FOL]}
LP = {c: np.log(v.astype(np.float64)).astype(np.float32) for c, v in P.items()}
del P
SPLIT = 30 * S
print(f"{ND} days {days[0]}..{days[-1]}, fit = first 30 days, test = last {ND - 30}", flush=True)

# beta per follower per day from the previous day's 60 s returns
BETA = {}
for c in FOL:
    b = np.full(ND, np.nan)
    for k in range(1, ND):
        sl = slice((k - 1) * S, k * S, 60)
        xb, xf = np.diff(LP["BTC"][sl]), np.diff(LP[c][sl])
        b[k] = (xb * xf).sum() / (xb * xb).sum()
    BETA[c] = np.repeat(b, S).astype(np.float32)
    print(f"  beta {c}: median {np.nanmedian(b):.2f}", flush=True)


def trades(L, q, g, H):
    out = []                                              # (follower, t, gross)
    B = LP["BTC"]
    rB = np.full_like(B, np.nan)
    rB[L:] = B[L:] - B[:-L]
    for c in FOL:
        F = LP[c]
        rF = np.full_like(F, np.nan)
        rF[L:] = F[L:] - F[:-L]
        sgn = np.sign(rB)
        gap = sgn * (BETA[c] * rB - rF)
        idx = np.flatnonzero((np.abs(rB) >= q / 1e4) & (gap >= g / 1e4))
        idx = idx[idx + 1 + 600 < len(F)]
        last = -10**9
        for t in idx:
            if t - last < 60:
                continue
            last = t
            out.append((c, t, sgn[t] * (F[t + 1 + H] - F[t + 1]), sgn[t]))
    return out


def stats(rows, side):
    if not rows:
        return 0, 0.0, 0.0
    net = np.array([r[2] for r in rows]) * 100 - 2 * side * 100
    pf = net[net > 0].sum() / max(1e-9, -net[net < 0].sum())
    return len(net), float(net.mean()), float(pf)


GRID = list(itertools.product((30, 60), (15, 25, 40), (10, 20), (60, 180, 600)))
res, best = [], None
for p in GRID:
    rows = [r for r in trades(*p) if r[1] >= S]           # day 1 has no beta
    fi, te = [r for r in rows if r[1] < SPLIT], [r for r in rows if r[1] >= SPLIT]
    nf, af, _ = stats(fi, 0.001)
    nt, at, pft = stats(te, 0.001)
    gt = float(np.mean([r[2] for r in te]) * 100) if te else 0.0
    res.append({"L": p[0], "q": p[1], "g": p[2], "H": p[3], "fit_n": nf, "fit_net": round(af, 3), "test_n": nt,
                "test_gross": round(gt, 3), "test_net": round(at, 3), "test_pf": round(pft, 2)})
    if nf and (best is None or af * nf > best[0]):
        best = (af * nf, p, te)
    print(f"L{p[0]:3} q{p[1]:3} g{p[2]:3} H{p[3]:4} | fit n {nf:5} net {af:+.3f}% | test n {nt:5} gross {gt:+.3f}% "
          f"net {at:+.3f}% PF {pft:4.2f}", flush=True)

_, p, te = best
B = LP["BTC"]
mk = {}
for h in (1, 5, 15, 60, 180):
    mk[h] = round(float(np.mean([r[3] * (LP[r[0]][r[1] + 1 + h] - LP[r[0]][r[1] + 1]) for r in te]) * 100), 4)
n10, a10, pf10 = stats(te, 0.001)
n05, a05, pf05 = stats(te, 0.0005)
pos = sum(1 for r in res if r["test_n"] and r["test_net"] > 0)
fit_best = next(r for r in res if (r["L"], r["q"], r["g"], r["H"]) == p)
ok = n10 >= 100 and a10 > 0 and pf10 >= 1.2 and pos >= len(GRID) / 2 and fit_best["fit_net"] > 0
print(f"\nchosen on fit {p}: test n {n10}, net {a10:+.3f}% PF {pf10:.2f} at 0.10%/side | {a05:+.3f}% PF {pf05:.2f} at "
      f"0.05%/side | markouts (gross %, after entry) {mk} | settings net+ on test {pos}/{len(GRID)} | "
      f"{'PASS' if ok else 'fail'}")
(Path(__file__).parent / "leadlag_results.json").write_text(json.dumps(
    {"chosen": p, "test_n": n10, "test_net_010": a10, "test_pf_010": pf10, "test_net_005": a05, "test_pf_005": pf05,
     "markouts": mk, "settings_positive": f"{pos}/{len(GRID)}", "pass": ok, "grid": res}, indent=1), encoding="utf-8")
