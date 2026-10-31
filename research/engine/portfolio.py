"""Portfolio construction from the qualifying strategy pool.

Requirement #25: don't just pick one winner. Select a set whose returns are not
copies of each other, then measure the combined result on the holdout coins.

Selection rules:
  * candidate pool = qualifies on frequency + quality gates, deduplicated by
    behaviour (identical trade counts/return/PF means a non-binding filter, not
    a different strategy);
  * greedy by score, rejecting any candidate whose monthly-return correlation
    with an already-chosen member exceeds `max_corr`;
  * at most `family_cap` members from one family, so a single idea cannot fill
    the whole portfolio;
  * the chosen set is then re-simulated on the holdout coins and combined
    equal-weight.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest import simulate                                   # noqa: E402
from features import DEV_COINS, HOLDOUT_COINS, load_universe    # noqa: E402
from generate import generate, to_config                        # noqa: E402
from tournament import (EQUITY, metrics, period_consistency)    # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "engine_results"
SPAN = 5.7
LEVERAGE = 1.0          # the deployed candidate runs unlevered
MAX_CORR = 0.5
FAMILY_CAP = 2
POOL = 120              # top-N distinct candidates to simulate


def monthly(trades, dates) -> pd.Series:
    rows: dict[str, float] = {}
    for t in trades:
        d = pd.Timestamp(dates[min(t.exit_i, len(dates) - 1)])
        if d.tzinfo is not None:
            d = d.tz_localize(None)
        rows[f"{d.year}-{d.month:02d}"] = rows.get(f"{d.year}-{d.month:02d}", 0.0) + t.pnl
    return pd.Series(rows).sort_index() / EQUITY * 100


def main():
    rank = json.loads((OUT / "full_rank_dev.json").read_text())
    q = [r for r in rank
         if r["trades"] >= 570 and r["ret_pct"] > 0
         and r["pf"] >= 1.15 and r["max_dd"] <= 35]
    # dedupe: same behaviour == same strategy
    seen, distinct = set(), []
    for r in sorted(q, key=lambda r: -r["score"]):
        key = (r["trades"], round(r["ret_pct"], 1), round(r["pf"], 2))
        if key in seen:
            continue
        seen.add(key)
        distinct.append(r)
    print(f"qualifying {len(q)} -> distinct {len(distinct)}; simulating top {POOL}",
          flush=True)

    by_id = {c["id"]: c for c in generate(short_modes=["sym", "off", "weakdn", "tp_weakdn"])}
    universe = load_universe(DEV_COINS)
    dates = next(iter(universe.values())).date

    pool = []
    for r in distinct[:POOL]:
        c = by_id.get(r["id"])
        if not c:
            continue
        tr = simulate(universe, c["spec"], to_config(c["cfg"], LEVERAGE))
        m = metrics(tr)
        if m["trades"] < 570 or m["ret_pct"] <= 0 or m.get("liquidations", 0):
            continue
        pool.append({"id": r["id"], "fam": r["id"].split("|")[0], "cand": c,
                     "trades": tr, "m": m, "ser": monthly(tr, dates)})
    print(f"pool simulated: {len(pool)}", flush=True)
    if not pool:
        print("no eligible members")
        return

    idx = sorted(set().union(*[set(p["ser"].index) for p in pool]))
    mat = pd.DataFrame({p["id"]: p["ser"].reindex(idx).fillna(0) for p in pool})

    # ---- greedy low-correlation selection with a family cap ----
    chosen, fam_count = [], {}
    for p in pool:                      # pool is already score-ordered
        if fam_count.get(p["fam"], 0) >= FAMILY_CAP:
            continue
        if chosen:
            c = max(abs(mat[p["id"]].corr(mat[o["id"]])) for o in chosen)
            if np.isnan(c) or c > MAX_CORR:
                continue
        chosen.append(p)
        fam_count[p["fam"]] = fam_count.get(p["fam"], 0) + 1
        if len(chosen) >= 6:
            break

    print(f"\nPORTFOLIO ({len(chosen)} members, max pairwise corr {MAX_CORR}, "
          f"<= {FAMILY_CAP} per family)")
    for p in chosen:
        m = p["m"]
        print(f"  {m['trades']/SPAN:>5.0f}/yr  ret {m['ret_pct']:>7.1f}%  PF {m['pf']:>5.2f}  "
              f"DD {m['max_dd']:>5.1f}%  {p['id'][:78]}")

    if len(chosen) > 1:
        cm = mat[[p["id"] for p in chosen]].corr()
        cm.index = [f"S{i+1}" for i in range(len(chosen))]
        cm.columns = list(cm.index)
        print("\ncorrelation of monthly returns:")
        print(cm.round(2).to_string())

    # ---- combined, equal weight ----
    def combine(members, uni, dts, label):
        all_tr = []
        for p in members:
            tr = p["trades"] if uni is universe else \
                simulate(uni, p["cand"]["spec"], to_config(p["cand"]["cfg"], LEVERAGE))
            all_tr.extend(tr)
        n = len(members)
        pnl = np.array([t.pnl for t in all_tr]) / n      # equal weight
        ser = pd.Series(pnl, index=[t.exit_i for t in all_tr]).sort_index()
        eq = EQUITY + ser.cumsum()
        dd = float(((eq.cummax() - eq) / eq.cummax()).max() * 100)
        w = pnl[pnl > 0].sum()
        l = abs(pnl[pnl < 0].sum())
        print(f"\n{label}: {len(all_tr)} trades ({len(all_tr)/SPAN:.0f}/yr), "
              f"return {pnl.sum()/EQUITY*100:+.1f}%, PF {w/l if l else 0:.2f}, "
              f"max DD {dd:.1f}%")
        return {"trades": len(all_tr), "ret_pct": round(pnl.sum() / EQUITY * 100, 2),
                "pf": round(w / l, 3) if l else 0, "max_dd": round(dd, 2)}

    dev_res = combine(chosen, universe, dates, "COMBINED (dev coins)")
    hold_u = load_universe(HOLDOUT_COINS)
    hold_dates = next(iter(hold_u.values())).date
    hold_res = combine(chosen, hold_u, hold_dates, "COMBINED (holdout coins, unseen)")

    # single best member, for comparison
    best = chosen[0]["m"]
    print(f"\nbest single member (dev): ret {best['ret_pct']:+.1f}%  PF {best['pf']}  "
          f"DD {best['max_dd']}%")
    json.dump({"members": [p["id"] for p in chosen],
               "dev": dev_res, "holdout": hold_res},
              open(OUT / "portfolio_final.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
