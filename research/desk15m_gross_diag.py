"""POST-HOC DIAGNOSTIC for the 2026-09-27 desk15m run - NOT a gate, cannot validate anything.

Question: did the 192 pre-registered combinations have any edge BEFORE costs, or
none at all? Runs them on dev coins x dev period with zero fees, zero slippage
and zero funding. The sealed quadrant is not touched.
"""
import collections
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import desk15m_run as R  # noqa: E402

ZERO = {"fee": 0.0, "slip": 0.0}

feats = {}
for sym in R.DEV:
    coin = R.load_coin(sym)
    for tf in R.TFS:
        k = R.bars(coin, tf)                          # features still see funding (family X needs it)
        m = ((k["date"] >= R.DEV_START) & (k["date"] < R.SEAL_START)).to_numpy()
        sigs = {(fam, d, json.dumps(ep, sort_keys=True)): R.signal(k, fam, d, ep) & m
                for fam, eps in R.FAMILIES.items() for ep in eps for d in R.DIRS}
        # ...but the simulator gets an empty funding table, so no funding is CHARGED
        feats[(sym, tf)] = (R.to_arr(k, coin["funding"].iloc[0:0]), sigs)

rows = []
for fam, eps in R.FAMILIES.items():
    for ep in eps:
        for d in R.DIRS:
            for tf in R.TFS:
                for xp in R.EXITS:
                    rs = []
                    for sym in R.DEV:
                        a, sigs = feats[(sym, tf)]
                        _, r = R.simulate(a, np.flatnonzero(sigs[(fam, d, json.dumps(ep, sort_keys=True))]),
                                          d, xp["s"], xp["r"], ZERO)
                        rs.append(r)
                    r = np.concatenate(rs)
                    rows.append({"id": R.cid(fam, d, tf, ep, xp), "family": fam, "direction": d, "tf": tf,
                                 "trades": len(r), "gross_exp_R": round(float(r.mean()), 4) if len(r) else None,
                                 "gross_pf": round(R.pf(r), 4) if len(r) else None})

out = {"note": "post-hoc diagnostic, zero costs, dev coins x dev period; not a gate", "rows": rows}
(R.OUT / "desk15m_gross_diag.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
pos = [r for r in rows if r["gross_exp_R"] and r["gross_exp_R"] > 0]
print(f"combos with positive GROSS expectancy: {len(pos)} of {len(rows)}")
best = collections.defaultdict(lambda: None)
for r in rows:
    k = (r["family"], r["direction"], r["tf"])
    if r["gross_exp_R"] is not None and (best[k] is None or r["gross_exp_R"] > best[k]["gross_exp_R"]):
        best[k] = r
for k in sorted(best):
    b = best[k]
    print(f"  {k}: best gross exp {b['gross_exp_R']:+.4f} R  pf {b['gross_pf']}  n {b['trades']}")
