"""Funding carry, hedged. Rule: ../REGISTER_CARRY_2026-10-25.md.

    .venv\\Scripts\\python.exe research\\fresh\\carry\\run.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import bear_batch as bb  # noqa: E402

S, E = pd.Timestamp("2022-02-07", tz="UTC"), pd.Timestamp("2026-09-28", tz="UTC")
K, MINF, NOTION, MARGIN, COST, SQZ = 5, 0.0001, 40.0, 20.0, 0.003, 0.40

FR, HI, CL = {}, {}, {}
for p in bb.PAIRS:
    b = p.split("/")[0]
    f = bb.DATA / f"{b}_USDT_USDT-1h-funding_rate.feather"
    g = bb.DATA / f"{b}_USDT_USDT-1h-futures.feather"
    if f.exists() and g.exists():
        FR[p] = pd.read_feather(f).set_index("date")["funding_rate"]
        d = pd.read_feather(g).set_index("date")
        HI[p], CL[p] = d["high"], d["close"]
FR = pd.DataFrame(FR).sort_index()
HI, CL = pd.DataFrame(HI).sort_index(), pd.DataFrame(CL).sort_index()
rows, held = [], set()
for w in pd.date_range(S, E - pd.Timedelta(days=7), freq="7D", tz="UTC"):
    past = FR[(FR.index >= w - pd.Timedelta(days=7)) & (FR.index < w)]
    nxt = FR[(FR.index >= w) & (FR.index < w + pd.Timedelta(days=7))]
    avg = past.mean().dropna()
    pick = list(avg[avg >= MINF].nlargest(K).index)
    usdt = -COST * NOTION * (len(set(pick) - held) + len(held - set(pick)))
    liq = 0
    keep = set()
    for p in pick:
        fund = float(nxt[p].fillna(0).sum()) * NOTION                 # short perp receives positive funding
        p0 = CL[p].asof(w)
        hi = HI[p][(HI.index >= w) & (HI.index < w + pd.Timedelta(days=7))].max()
        if p0 and hi / p0 - 1 >= SQZ:
            usdt += -MARGIN + NOTION * SQZ - COST * NOTION + fund * 0.5
            liq += 1
            continue
        usdt += fund
        keep.add(p)
    held = keep
    rows.append((w, len(pick), usdt, liq))
W = pd.DataFrame(rows, columns=["week", "coins", "usdt", "liq"]).set_index("week")
eq = 300 + W.usdt.cumsum()
dd = float((eq / eq.cummax() - 1).min())
yr = W.groupby(W.index.year)["usdt"].sum()
years = len(W) / 52.18
ok = W.usdt.sum() / 300 / years >= 0.10 and (yr > 0).all() and dd >= -0.05
out = {"weeks": len(W), "net_usdt": round(float(W.usdt.sum()), 1), "pct_per_year": round(float(W.usdt.sum() / 300 / years * 100), 1),
       "years_usdt": {int(k): round(float(v), 1) for k, v in yr.items()}, "max_dd_pct": round(dd * 100, 1),
       "weeks_red_pct": round(float((W.usdt < 0).mean() * 100), 1), "avg_coins": round(float(W.coins.mean()), 1),
       "squeezes": int(W.liq.sum()), "last52_usdt": round(float(W.usdt.tail(52).sum()), 1),
       "verdict": "🟡 paper forward test" if ok else "🔴"}
W.to_csv(HERE / "weeks.csv")
(HERE / "result.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out))
