"""Walk-forward under the PF-based selection rule declared in
PREREGISTRATION_2026-09-21.md.

Runs both selectors over identical folds, candidates and data so the only
variable is the selection statistic. Reports portfolio-level folds positive,
which is the pre-registered criterion.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "engine"))
from backtest import Config, simulate            # noqa: E402
from features import load_pair                   # noqa: E402
from gate_run import (CANDIDATES, CONTROLS, FOLDS, WALLET,  # noqa: E402
                      CFG, portfolio, ts)

UNI = ROOT / "data" / "market" / "universe"
OUT = HERE / "engine_results" / "wf_pf_results.json"
import sys as _s
if "--set" in _s.argv and "holdout" in _s.argv:
    OUT = HERE / "engine_results" / "wf_pf_holdout.json"
MIN_TRADES_FOLD = 100          # declared eligibility floor


def load_dev(setname="dev"):
    split = json.loads((UNI / "split_140.json").read_text(encoding="utf-8"))
    uni = {}
    for c in split[setname]:
        f = load_pair(c, futures=True)
        if f is not None and len(f.close) >= 400:
            uni[c] = f
    return uni


def pf_of(df):
    w = df[df.pnl > 0].pnl.sum()
    l = -df[df.pnl < 0].pnl.sum()
    return (w / l) if l > 0 else None


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="dev", choices=["dev", "holdout"])
    args = ap.parse_args()
    uni = load_dev(args.set)
    print(f"{args.set} coins: {len(uni)}", flush=True)
    if args.set == "holdout":
        print("CLEAN TEST: the PF selector declared in PREREGISTRATION_2026-09-21.md\n"
              "has never been applied to these coins fold-by-fold.\n", flush=True)
    else:
        print("", flush=True)
    allc = CANDIDATES + CONTROLS

    cache = {}
    for cid, fam, filts, direction, params in allc:
        spec = {"family": fam, "direction": direction, "filters": filts,
                "trend_mode": "with", "params": params}
        tr = simulate(uni, spec, Config(**CFG))
        rows = [{"pair": t.pair, "pnl": t.pnl, "notional": t.notional,
                 "entry": pd.Timestamp(uni[t.pair].date[t.entry_i]),
                 "exit": pd.Timestamp(uni[t.pair].date[min(t.exit_i, len(uni[t.pair].date) - 1)])}
                for t in tr]
        d = pd.DataFrame(rows)
        d["entry"] = pd.to_datetime(d.entry, utc=True)
        d["exit"] = pd.to_datetime(d.exit, utc=True)
        cache[cid] = d
        print(f"  simulated {cid:38} {len(d):>6} trades", flush=True)

    results = {}
    for rule in ("raw_return", "profit_factor"):
        folds, agg_sum, pf_sum = [], 0.0, 0.0
        for a, split, b in FOLDS:
            best, bestscore = None, -1e9
            for cid, df in cache.items():
                tr = df[(df.entry >= ts(a)) & (df.entry < ts(split))]
                if rule == "profit_factor":
                    if len(tr) < MIN_TRADES_FOLD:     # declared floor
                        continue
                    score = pf_of(tr)
                    if score is None:
                        continue
                else:
                    if len(tr) < 30:
                        continue
                    score = tr.pnl.sum() / WALLET * 100
                if score > bestscore:
                    best, bestscore = cid, score
            oos = cache[best][(cache[best].entry >= ts(split)) & (cache[best].entry < ts(b))]
            o = oos.pnl.sum() / WALLET * 100
            p = portfolio(oos, 10)
            agg_sum += o
            pf_sum += p["ret_pct"]
            folds.append({"oos": f"{split}->{b}", "picked": best,
                          "train_score": round(bestscore, 3),
                          "oos_agg": round(o, 1), "oos_portfolio": p["ret_pct"],
                          "oos_dd": p["max_dd"], "oos_trades": int(len(oos))})
        pos_a = sum(1 for f in folds if f["oos_agg"] > 0)
        pos_p = sum(1 for f in folds if f["oos_portfolio"] > 0)
        results[rule] = {"folds": folds, "agg_sum": round(agg_sum, 1),
                         "portfolio_sum": round(pf_sum, 1),
                         "folds_positive_agg": f"{pos_a}/{len(FOLDS)}",
                         "folds_positive_portfolio": f"{pos_p}/{len(FOLDS)}"}

        print(f"\n{'='*112}\nSELECTOR: {rule}\n{'='*112}")
        print(f"{'oos window':24}{'picked':38}{'train':>10}{'OOS agg':>10}{'OOS pf':>9}{'DD%':>8}{'trades':>8}")
        for f in folds:
            print(f"{f['oos']:24}{f['picked']:38}{f['train_score']:>10}"
                  f"{f['oos_agg']:>10}{f['oos_portfolio']:>9}{f['oos_dd']:>8}{f['oos_trades']:>8}")
        print(f"\n  aggregate  sum {agg_sum:+.1f}%   folds positive {pos_a}/{len(FOLDS)}")
        print(f"  PORTFOLIO  sum {pf_sum:+.1f}%   folds positive {pos_p}/{len(FOLDS)}   <-- criterion")

    a = results["raw_return"]["folds_positive_portfolio"]
    b = results["profit_factor"]["folds_positive_portfolio"]
    print(f"\n{'='*112}")
    print(f"PRE-REGISTERED CRITERION: portfolio folds positive, PF rule must beat raw return")
    print(f"  raw_return    {a}")
    print(f"  profit_factor {b}")
    ra, rb = int(a.split('/')[0]), int(b.split('/')[0])
    print(f"  VERDICT: {'PF rule wins' if rb > ra else 'PF rule does NOT beat raw return' if rb < ra else 'no difference'}")
    OUT.write_text(json.dumps(results, indent=1, default=float), encoding="utf-8")
    print(f"\nwrote {OUT}\nWF_PF_COMPLETE")


if __name__ == "__main__":
    main()
