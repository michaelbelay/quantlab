"""Full validation gauntlet: does dropping `btc_regime` beat the live spec?

Decision rule is pre-registered in PREREGISTRATION_2026-09-23_btcregime.md and is
NOT restated loosely here - it is encoded below and evaluated mechanically, so
the verdict cannot drift to fit the numbers.

Two specs, identical but for the filter list, on the 63 holdout coins:

    LIVE       btc_regime + volume      (what the live bot ran then)
    CANDIDATE  volume only

Nothing here touches the live bot. Offline simulation only.

    python research/btcregime_gauntlet.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "engine"))
from gate_run import (FOLDS, REGIMES, WALLET, agg_stats, load_set,  # noqa: E402
                      portfolio, run_variant, ts)

SLOTS = 20          # the live book
OUT = HERE / "engine_results" / "btcregime_gauntlet.json"

SPECS = {
    "LIVE  btc_regime+volume": ["btc_regime", "volume"],
    "CANDIDATE  volume only": ["volume"],
}


def spec_for(filters):
    return {"family": "volatility_breakout", "direction": "both",
            "filters": filters, "trend_mode": "with",
            "params": {"bars": 4, "atr_mult": 2.0}}


def evaluate(uni, filters):
    spec = spec_for(filters)
    base = run_variant(uni, spec)
    out = {
        "aggregate": agg_stats(base),
        "cost2x": agg_stats(run_variant(uni, spec, fee_mult=2.0, slip_mult=2.0)),
        "slip2x": agg_stats(run_variant(uni, spec, slip_mult=2.0)),
        "funding2x": agg_stats(run_variant(uni, spec, funding_mult=2.0)),
        "portfolio_20": portfolio(base, SLOTS),
        "portfolio_10": portfolio(base, 10),
        "funding_paid": round(base.funding.sum(), 1) if not base.empty else 0.0,
        "expectancy": round(base.pnl.mean(), 4) if not base.empty else 0.0,
        "win_pct": round((base.pnl > 0).mean() * 100, 1) if not base.empty else 0.0,
    }
    yrs = (base.entry.max() - base.entry.min()).days / 365.25
    out["trades_per_year"] = round(len(base) / yrs)
    for name, s, e in REGIMES:
        sub = base[(base.entry >= ts(s)) & (base.entry < ts(e))]
        out[name] = round(sub.pnl.sum() / WALLET * 100, 1)
    # Walk-forward. No selection happens here - both specs are FIXED - so these
    # are straight out-of-sample time slices, which is the honest test for a
    # change to an already-chosen strategy.
    folds = []
    for _a, split, b in FOLDS:
        oos = base[(base.entry >= ts(split)) & (base.entry < ts(b))]
        p = portfolio(oos, SLOTS)
        folds.append({"window": f"{split[:7]}->{b[:7]}", "trades": int(len(oos)),
                      "agg_ret": round(oos.pnl.sum() / WALLET * 100, 1),
                      "pf_ret": p["ret_pct"], "pf_dd": p["max_dd"]})
    out["folds"] = folds
    out["wf_oos_sum"] = round(sum(f["pf_ret"] for f in folds), 1)
    out["wf_folds_positive"] = sum(1 for f in folds if f["pf_ret"] > 0)
    return out


def verdict(live: dict, cand: dict) -> tuple[bool, list[tuple[str, bool, str]]]:
    """The pre-registered rule, evaluated mechanically."""
    g = []
    g.append(("GATE 1  2x costs PF >= 1.10", (cand["cost2x"]["pf"] or 0) >= 1.10,
              f"{cand['cost2x']['pf']}"))
    g.append(("GATE 2  2x funding PF > 1.00", (cand["funding2x"]["pf"] or 0) > 1.0,
              f"{cand['funding2x']['pf']}"))
    g.append(("GATE 3  2x slippage PF > 1.00", (cand["slip2x"]["pf"] or 0) > 1.0,
              f"{cand['slip2x']['pf']}"))
    regs = [cand[n] for n, _, _ in REGIMES]
    g.append(("GATE 4  positive in all 4 regimes", all(r > 0 for r in regs),
              " ".join(f"{n}={cand[n]:+.1f}" for n, _, _ in REGIMES)))
    g.append(("GATE 5  WF sum > 0 and >= 4/8 folds",
              cand["wf_oos_sum"] > 0 and cand["wf_folds_positive"] >= 4,
              f"sum {cand['wf_oos_sum']:+.1f}%, {cand['wf_folds_positive']}/8 folds"))
    g.append(("SUP 6   portfolio-20 return >= LIVE",
              cand["portfolio_20"]["ret_pct"] >= live["portfolio_20"]["ret_pct"],
              f"{cand['portfolio_20']['ret_pct']:+.1f}% vs LIVE {live['portfolio_20']['ret_pct']:+.1f}%"))
    g.append(("SUP 7   portfolio-20 max DD <= LIVE",
              cand["portfolio_20"]["max_dd"] <= live["portfolio_20"]["max_dd"],
              f"{cand['portfolio_20']['max_dd']:.1f}% vs LIVE {live['portfolio_20']['max_dd']:.1f}%"))
    g.append(("SUP 8   WF OOS sum >= LIVE",
              cand["wf_oos_sum"] >= live["wf_oos_sum"],
              f"{cand['wf_oos_sum']:+.1f}% vs LIVE {live['wf_oos_sum']:+.1f}%"))
    return all(ok for _, ok, _ in g), g


def main() -> int:
    hold, na = load_set("holdout")
    print(f"holdout: {len(hold)} coins with usable history"
          + (f"   unavailable ({len(na)}): {' '.join(na)}" if na else ""), flush=True)
    print(f"book size for portfolio tests: {SLOTS} slots\n", flush=True)

    res = {}
    for label, filters in SPECS.items():
        print(f"  running {label} ...", flush=True)
        res[label] = evaluate(hold, filters)

    live = res["LIVE  btc_regime+volume"]
    cand = res["CANDIDATE  volume only"]

    print("\n" + "=" * 92)
    print(f"  HOLDOUT GAUNTLET - 63 unseen coins")
    print("=" * 92)
    rows = [
        ("trades", "aggregate", "trades"), ("trades/year", None, "trades_per_year"),
        ("aggregate ret %", "aggregate", "ret_pct"), ("profit factor", "aggregate", "pf"),
        ("expectancy/trade", None, "expectancy"), ("win %", None, "win_pct"),
        ("PF at 2x costs", "cost2x", "pf"), ("PF at 2x slippage", "slip2x", "pf"),
        ("PF at 2x funding", "funding2x", "pf"), ("funding paid", None, "funding_paid"),
        ("portfolio-20 ret %", "portfolio_20", "ret_pct"),
        ("portfolio-20 max DD %", "portfolio_20", "max_dd"),
        ("portfolio-20 refused", "portfolio_20", "skipped"),
        ("portfolio-10 ret %", "portfolio_10", "ret_pct"),
        ("portfolio-10 max DD %", "portfolio_10", "max_dd"),
        ("WF OOS sum %", None, "wf_oos_sum"), ("WF folds positive", None, "wf_folds_positive"),
    ] + [(n, None, n) for n, _, _ in REGIMES]
    print(f"{'metric':<26}{'LIVE':>16}{'CANDIDATE':>16}{'delta':>14}")
    print("-" * 92)
    for label, grp, key in rows:
        lv = live[grp][key] if grp else live[key]
        cv = cand[grp][key] if grp else cand[key]
        try:
            d = f"{cv - lv:+.3f}".rstrip("0").rstrip(".")
        except Exception:
            d = ""
        print(f"{label:<26}{str(lv):>16}{str(cv):>16}{d:>14}")

    print("\n" + "=" * 92)
    print("  PER-FOLD OUT-OF-SAMPLE (portfolio-20 return %)")
    print("=" * 92)
    print(f"{'window':<20}{'LIVE':>12}{'CANDIDATE':>12}{'LIVE DD':>12}{'CAND DD':>12}")
    for lf, cf in zip(live["folds"], cand["folds"]):
        print(f"{lf['window']:<20}{lf['pf_ret']:>12}{cf['pf_ret']:>12}"
              f"{lf['pf_dd']:>12}{cf['pf_dd']:>12}")

    ok, gates = verdict(live, cand)
    print("\n" + "=" * 92)
    print("  PRE-REGISTERED DECISION RULE")
    print("=" * 92)
    for name, passed, detail in gates:
        print(f"  [{'PASS' if passed else 'FAIL'}]  {name:<38} {detail}")
    print()
    if ok:
        print("  ALL GATES AND SUPERIORITY TESTS PASSED.")
        print("  The candidate is eligible. Adoption is still a separate, explicit decision.")
    else:
        failed = [n for n, p, _ in gates if not p]
        print("  VERDICT: REJECTED - keep VBreak4Live unchanged.")
        print(f"  Failed: {len(failed)} of {len(gates)}")
        for n in failed:
            print(f"    - {n}")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(
        {"holdout_coins": len(hold), "unavailable": na, "slots": SLOTS,
         "results": res, "adopted": ok,
         "gates": [{"name": n, "pass": p, "detail": d} for n, p, d in gates]},
        indent=1, default=float), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
