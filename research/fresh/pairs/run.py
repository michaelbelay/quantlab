"""Pairs trading, distance method, hourly. Rule: ../REGISTER_PAIRS_2026-10-25.md.

    .venv\\Scripts\\python.exe research\\fresh\\pairs\\run.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import bear_batch as bb  # noqa: E402

S, E = pd.Timestamp("2022-02-07", tz="UTC"), pd.Timestamp("2026-10-19", tz="UTC")
NLIQ, NPAIR, LEG, COST, ZIN, ZSTOP = 30, 10, 15.0, 0.002, 2.0, 4.0

C, QV = {}, {}
for p in bb.PAIRS:
    f = bb.DATA / f"{p.split('/')[0]}_USDT_USDT-1h-futures.feather"
    if f.exists():
        d = pd.read_feather(f).set_index("date").sort_index()
        C[p], QV[p] = d["close"], d["close"] * d["volume"]
C, QV = pd.DataFrame(C), pd.DataFrame(QV)
E = min(E, C.index[-1].normalize())
trades = []
for w in pd.date_range(S, E - pd.Timedelta(days=7), freq="7D", tz="UTC"):
    f0, f1, t1 = w - pd.Timedelta(days=30), w, w + pd.Timedelta(days=7)
    F = C[(C.index >= f0) & (C.index < f1)]
    full = F.columns[F.notna().all()]
    if len(full) < 2 * NPAIR:
        continue
    liq = QV.loc[F.index, full].median().nlargest(NLIQ).index
    N = F[liq] / F[liq].iloc[0]
    X = N.to_numpy()
    D = ((X[:, :, None] - X[:, None, :]) ** 2).sum(axis=0)
    iu = np.triu_indices(len(liq), 1)
    order = np.argsort(D[iu])
    used, pairs = set(), []
    for o in order:
        a, b = liq[iu[0][o]], liq[iu[1][o]]
        if a in used or b in used:
            continue
        used |= {a, b}
        pairs.append((a, b))
        if len(pairs) == NPAIR:
            break
    T = C[(C.index >= f1) & (C.index <= t1)]
    for a, b in pairs:
        fs = np.log(F[a]) - np.log(F[b])
        mu, sd = fs.mean(), fs.std()
        if not sd > 0:
            continue
        pa, pb = T[a].to_numpy(), T[b].to_numpy()
        z = ((np.log(pa) - np.log(pb)) - mu) / sd
        i, n = 0, len(z)
        while i < n - 1:
            if np.isnan(z[i]) or abs(z[i]) <= ZIN:
                i += 1
                continue
            sgn = 1 if z[i] > 0 else -1          # +1: A rich -> short A, long B
            j = i + 1
            while j < n - 1 and not np.isnan(z[j]) and z[j] * sgn > 0 and abs(z[j]) < ZSTOP:
                j += 1
            ra, rb = pa[j] / pa[i] - 1, pb[j] / pb[i] - 1
            if np.isnan(ra) or np.isnan(rb):
                break
            net = (-sgn * ra + sgn * rb) / 2 - COST        # % of pair notional (2 legs)
            reason = "stop" if abs(z[j]) >= ZSTOP else "cross" if z[j] * sgn <= 0 else "week_end"
            trades.append((T.index[i], T.index[j], a, b, j - i, net, net * 2 * LEG, reason))
            i = j + 1
Tr = pd.DataFrame(trades, columns=["open", "close", "a", "b", "hours", "net", "usdt", "reason"])
Tr.to_csv(HERE / "trades.csv", index=False)
daily = Tr.groupby(Tr["close"].dt.normalize())["usdt"].sum()
eq = 300 + daily.cumsum()
dd = float((eq / eq.cummax() - 1).min())
yr = Tr.groupby(Tr["close"].dt.year)["usdt"].sum()
last12 = float(Tr.loc[Tr["close"] >= E - pd.Timedelta(days=365), "usdt"].sum())
ok = Tr.usdt.sum() > 0 and Tr.net.mean() >= 0.003 and (yr > 0).sum() >= 4 and last12 > 0 and dd >= -0.20
out = {"trades": len(Tr), "net_usdt": round(float(Tr.usdt.sum()), 1), "avg_net_pct": round(float(Tr.net.mean()) * 100, 3),
       "win_pct": round(float((Tr.net > 0).mean()) * 100, 1), "years_usdt": {int(k): round(float(v), 1) for k, v in yr.items()},
       "last12_usdt": round(last12, 1), "max_dd_pct": round(dd * 100, 1), "avg_hold_h": round(float(Tr.hours.mean()), 1),
       "max_hold_h": int(Tr.hours.max()), "avg_win_usdt": round(float(Tr.loc[Tr.usdt > 0, "usdt"].mean()), 2),
       "avg_loss_usdt": round(float(Tr.loc[Tr.usdt <= 0, "usdt"].mean()), 2), "exits": Tr.reason.value_counts().to_dict(),
       "verdict": "🟡 paper forward test" if ok else "🔴"}
(HERE / "result.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out))
