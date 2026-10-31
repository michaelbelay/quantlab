"""Tournament driver: generate -> simulate -> rank -> walk-forward -> robustness.

Walk-forward note: the only thing being fitted here is strategy SELECTION, and
no strategy parameter is derived from the data. So one full-history simulation
per candidate can be sliced by window -- selection uses the train slice, the
score that counts comes from the following slice, which selection never saw.
Indicators only ever look backwards, so slicing introduces no leakage.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest import simulate                                  # noqa: E402
from features import DEV_COINS, HOLDOUT_COINS, load_universe   # noqa: E402
from generate import generate, to_config                       # noqa: E402
from tournament import (EQUITY, composite, metrics, period_consistency,  # noqa: E402
                        regime_breakdown)

OUT = Path(__file__).resolve().parents[1] / "engine_results"
OUT.mkdir(exist_ok=True)

# train -> out-of-sample, rolled forward; selection only ever sees `train`
WINDOWS = [
    ("2021-01-01", "2022-07-01", "2022-07-01", "2023-01-01"),
    ("2021-07-01", "2023-01-01", "2023-01-01", "2023-07-01"),
    ("2022-01-01", "2023-07-01", "2023-07-01", "2024-01-01"),
    ("2022-07-01", "2024-01-01", "2024-01-01", "2024-07-01"),
    ("2023-01-01", "2024-07-01", "2024-07-01", "2025-01-01"),
    ("2023-07-01", "2025-01-01", "2025-01-01", "2025-07-01"),
    ("2024-01-01", "2025-07-01", "2025-07-01", "2026-01-01"),
    ("2024-07-01", "2026-01-01", "2026-01-01", "2026-10-01"),
]


def slice_trades(trades, dates, lo, hi):
    # dates come from .values and are tz-naive UTC; keep the bounds naive too
    a, b = pd.Timestamp(lo), pd.Timestamp(hi)
    out = []
    for t in trades:
        d = pd.Timestamp(dates[min(t.exit_i, len(dates) - 1)])
        if d.tzinfo is not None:
            d = d.tz_localize(None)
        if a <= d < b:
            out.append(t)
    return out


def simulate_all(universe, candidates, leverage=2.0, log_every=50):
    """One full-history simulation per candidate."""
    res = {}
    t0 = time.time()
    for k, c in enumerate(candidates):
        try:
            tr = simulate(universe, c["spec"], to_config(c["cfg"], leverage))
        except Exception as exc:
            res[c["id"]] = {"error": f"{type(exc).__name__}: {exc}", "trades": []}
            continue
        res[c["id"]] = {"trades": tr, "cand": c}
        if log_every and (k + 1) % log_every == 0:
            print(f"  simulated {k+1}/{len(candidates)}  ({time.time()-t0:.0f}s)", flush=True)
    return res


def evaluate(trades, universe):
    m = metrics(trades)
    cons, buckets = period_consistency(trades, universe)
    sc = composite(m, cons)
    return m, cons, buckets, sc


def main(leverage=2.0, tag="dev"):
    print(f"=== tournament ({tag}, leverage {leverage}x) ===", flush=True)
    universe = load_universe(DEV_COINS)
    dates = next(iter(universe.values())).date
    # short treatments in the grid: sym is the control, the others are the
    # fixes derived from the payoff/regime diagnosis
    cands = generate(short_modes=['sym', 'off', 'weakdn', 'tp_weakdn'])
    print(f"{len(cands)} candidates, {len(universe)} pairs", flush=True)

    sims = simulate_all(universe, cands)
    print("simulation done", flush=True)

    # ---------- full-period ranking ----------
    rows = []
    for sid, s in sims.items():
        if "error" in s:
            continue
        m, cons, buckets, sc = evaluate(s["trades"], universe)
        rows.append({"id": sid, "score": sc.total, "terms": sc.terms,
                     "disq": sc.disqualified, "reason": sc.reason,
                     "consistency": round(cons, 3), "buckets": buckets, **m})
    df = pd.DataFrame(rows).sort_values("score", ascending=False)
    df.to_json(OUT / f"full_rank_{tag}.json", orient="records", indent=1)

    live = df[~df.disq]
    print(f"\nqualified: {len(live)}/{len(df)}   "
          f"(disqualified: {(df.disq).sum()} -- zero/low trades, unprofitable, liquidations)")
    print("\nTOP 15 BY COMPOSITE SCORE (full period, dev coins)")
    cols = ["id", "score", "trades", "ret_pct", "pf", "expectancy_r", "t_stat",
            "max_dd", "win_rate", "consistency"]
    print(live[cols].head(15).to_string(index=False, max_colwidth=58))

    # ---------- walk-forward: select on train, measure on the next slice ----------
    print("\n=== WALK-FORWARD (select on train, measure on unseen next window) ===",
          flush=True)
    wf_rows = []
    for (tr_lo, tr_hi, os_lo, os_hi) in WINDOWS:
        ranked = []
        for sid, s in sims.items():
            if "error" in s:
                continue
            tt = slice_trades(s["trades"], dates, tr_lo, tr_hi)
            if len(tt) < 25:                     # activity floor inside the window
                continue
            m = metrics(tt)
            m["disqualified"] = len(tt) < 25
            cons, _ = period_consistency(tt, universe)
            sc = composite(m, cons)
            if not sc.disqualified:
                ranked.append((sc.total, sid))
        ranked.sort(reverse=True)
        picks = [sid for _, sid in ranked[:5]]
        oos_pnl, oos_n = 0.0, 0
        for sid in picks:
            ot = slice_trades(sims[sid]["trades"], dates, os_lo, os_hi)
            oos_pnl += sum(t.pnl for t in ot)
            oos_n += len(ot)
        wf_rows.append({"train": f"{tr_lo[:7]}->{tr_hi[:7]}", "oos": f"{os_lo[:7]}->{os_hi[:7]}",
                        "candidates": len(ranked), "picks": picks,
                        "oos_pct": round(oos_pnl / (EQUITY * max(len(picks), 1)) * 100, 2),
                        "oos_trades": oos_n})
        print(f"  train {tr_lo[:7]}->{tr_hi[:7]}  oos {os_lo[:7]}->{os_hi[:7]}  "
              f"ranked={len(ranked):3}  oos={wf_rows[-1]['oos_pct']:+7.2f}%  "
              f"({oos_n} trades)  top={picks[0][:52] if picks else 'none'}", flush=True)

    stitched = sum(r["oos_pct"] for r in wf_rows)
    pos = sum(1 for r in wf_rows if r["oos_pct"] > 0)
    print(f"\nSTITCHED OUT-OF-SAMPLE: {stitched:+.2f}%  "
          f"({pos}/{len(wf_rows)} windows positive, equal-weight top-5 each window)")
    json.dump(wf_rows, open(OUT / f"walkforward_{tag}.json", "w"), indent=1)

    # ---------- robustness on the finalists ----------
    from robustness import (build_portfolio, cost_sensitivity,  # noqa: E402
                            parameter_stability)
    print("\n=== ROBUSTNESS (parameter neighbours, doubled costs, coin holdout) ===",
          flush=True)
    hold_u = load_universe(HOLDOUT_COINS)
    finals = []
    for _, row in live.head(8).iterrows():
        sid = row["id"]
        cand = sims[sid]["cand"]
        ps = parameter_stability(cand, universe, row["score"], leverage)
        cs = cost_sensitivity(cand, universe, leverage)
        ht = simulate(hold_u, cand["spec"], to_config(cand["cfg"], leverage))
        hm = metrics(ht)
        hcons, _ = period_consistency(ht, hold_u) if ht else (0.0, {})
        # re-score with the measured instability penalty applied
        rescored = composite({**row.to_dict(), "disqualified": False},
                             row["consistency"], instability=ps["instability"])
        finals.append({"id": sid, "base_score": row["score"],
                       "rescored": rescored.total, **ps, **cs,
                       "holdout_ret": hm["ret_pct"], "holdout_trades": hm["trades"],
                       "holdout_pf": hm["pf"], "holdout_dd": hm["max_dd"],
                       "holdout_consistency": round(hcons, 3)})
        f = finals[-1]
        print(f"  {sid[:56]:58} inst={f['instability']:.2f} "
              f"nbrs+={f['neighbours_profitable']}/{f['n']} "
              f"2xcost={f['ret_pct_2x_costs']:+7.1f}% "
              f"holdout={f['holdout_ret']:+7.1f}% ({f['holdout_trades']} tr)", flush=True)
    json.dump(finals, open(OUT / f"robustness_{tag}.json", "w"), indent=1)

    # ---------- portfolio ----------
    survivors = [f for f in finals
                 if f["ret_pct_2x_costs"] > 0 and f["holdout_ret"] > 0
                 and f["instability"] < 0.6 and f["neighbours_profitable"] >= f["n"] * 0.6]
    print(f"\nsurvived every robustness check: {len(survivors)}/{len(finals)}")
    if survivors:
        pf_in = [(s["id"], sims[s["id"]]["trades"]) for s in survivors]
        chosen, mat = build_portfolio(pf_in, dates)
        print("PORTFOLIO (low-correlation selection):")
        for c in chosen:
            print("   ", c[:90])
        if len(chosen) > 1:
            print("\ncorrelation of monthly returns:")
            print(mat[chosen].corr().round(2).to_string(max_colwidth=26))
        json.dump({"portfolio": chosen, "survivors": survivors},
                  open(OUT / f"portfolio_{tag}.json", "w"), indent=1)
    return df, sims, universe


if __name__ == "__main__":
    main()
