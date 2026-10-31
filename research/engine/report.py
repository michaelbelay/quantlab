"""Per-strategy reports, including the regime breakdown and a survival rationale.

Answers requirement #19 (where does this strategy actually work?) and #24
(full card per surviving strategy, including WHY it survived).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest import simulate                                   # noqa: E402
from features import DEV_COINS, HOLDOUT_COINS, load_universe    # noqa: E402
from generate import generate, to_config                        # noqa: E402
from robustness import cost_sensitivity, parameter_stability    # noqa: E402
from tournament import (EQUITY, composite, metrics,             # noqa: E402
                        period_consistency, regime_breakdown)

OUT = Path(__file__).resolve().parents[1] / "engine_results"


def vol_regime_split(trades, universe) -> dict:
    """P&L split by the volatility state at entry."""
    out = {}
    for t in trades:
        f = universe.get(t.pair)
        if f is None:
            continue
        st = str(f.regime["vol"].iat[t.entry_i])
        d = out.setdefault(st, {"n": 0, "pnl": 0.0})
        d["n"] += 1
        d["pnl"] += t.pnl
    return {k: {"n": v["n"], "pct": round(v["pnl"] / EQUITY * 100, 2)}
            for k, v in sorted(out.items())}


def card(cand: dict, universe, hold_u, leverage=2.0) -> dict:
    tr = simulate(universe, cand["spec"], to_config(cand["cfg"], leverage))
    m = metrics(tr)
    cons, buckets = period_consistency(tr, universe)
    sc = composite(m, cons)
    ps = parameter_stability(cand, universe, sc.total if not sc.disqualified else 0.0, leverage)
    cs = cost_sensitivity(cand, universe, leverage)
    ht = simulate(hold_u, cand["spec"], to_config(cand["cfg"], leverage))
    hm = metrics(ht)
    hcons, hbuckets = period_consistency(ht, hold_u) if ht else (0.0, {})
    spec, cfg = cand["spec"], cand["cfg"]
    return {
        "id": cand["id"], "family": spec["family"],
        "filters": spec["filters"], "trend_mode": spec["trend_mode"],
        "regime_gate": spec.get("regime"), "params": spec.get("params", {}),
        "timeframe": "1h", "direction": "long+short",
        "stop": f"{cfg.get('stop_mode')} x{cfg.get('stop_atr')}",
        "tp": f"{cfg.get('tp_mode')} {cfg.get('tp_atr')} frac {cfg.get('tp_frac')}",
        "breakeven_after_tp1": cfg.get("breakeven_after_tp1"),
        "trailing": cfg.get("trail_after_tp"), "entry_mode": cfg.get("entry_mode"),
        "score": sc.total, "score_terms": sc.terms, "score_explained": sc.explain(),
        "dev": m, "dev_consistency": round(cons, 3), "dev_halfyears": buckets,
        "dev_regime_pnl": regime_breakdown(tr), "dev_vol_regime_pnl": vol_regime_split(tr, universe),
        "holdout": hm, "holdout_consistency": round(hcons, 3), "holdout_halfyears": hbuckets,
        "holdout_regime_pnl": regime_breakdown(ht),
        "robustness": ps, "cost_stress": cs,
    }


def best_regime(d: dict) -> str:
    rp = d.get("dev_regime_pnl", {})
    if not rp:
        return "n/a"
    k = max(rp, key=lambda x: rp[x]["pct"])
    return f"{k} ({rp[k]['pct']:+.1f}%, {rp[k]['n']} trades)"


def why(d: dict) -> list[str]:
    r = []
    dev, ho, rb, cs = d["dev"], d["holdout"], d["robustness"], d["cost_stress"]
    if ho["ret_pct"] > 0:
        r.append(f"profitable on 8 coins never used in selection ({ho['ret_pct']:+.1f}%, "
                 f"{ho['trades']} trades, PF {ho['pf']})")
    if cs["ret_pct_2x_costs"] > 0:
        r.append(f"still profitable with fees and slippage doubled ({cs['ret_pct_2x_costs']:+.1f}%)")
    if rb["neighbours_profitable"] == rb["n"] and rb["n"]:
        r.append(f"all {rb['n']} nudged parameter variants stayed profitable "
                 f"(instability {rb['instability']})")
    if dev["trades"] >= 250:
        r.append(f"large sample ({dev['trades']} trades) -- not a small-sample artefact")
    if d["dev_consistency"] >= 0.6:
        r.append(f"positive in {int(d['dev_consistency']*100)}% of half-year periods")
    pos = [k for k, v in d["dev_regime_pnl"].items() if v["pct"] > 0]
    if len(pos) >= 3:
        r.append(f"profitable in {len(pos)} distinct trend regimes: {', '.join(pos)}")
    return r


def caveats(d: dict) -> list[str]:
    c = []
    dev, ho = d["dev"], d["holdout"]
    if dev["win_rate"] < 35:
        c.append(f"low win rate ({dev['win_rate']}%) -- relies on a few large winners, "
                 "psychologically hard and sensitive to missing the best trades")
    if ho["ret_pct"] < dev["ret_pct"] * 0.5:
        c.append(f"holdout return ({ho['ret_pct']:+.1f}%) well below dev "
                 f"({dev['ret_pct']:+.1f}%) -- some dev-set fitting remains")
    if d["robustness"]["instability"] > 0.3:
        c.append(f"parameter instability {d['robustness']['instability']}")
    neg = [k for k, v in d["dev_halfyears"].items() if v < 0]
    if neg:
        c.append(f"losing half-years: {', '.join(neg)}")
    if dev.get("max_consec_loss", 0) > 10:
        c.append(f"up to {dev['max_consec_loss']} consecutive losing trades")
    return c


def render(d: dict) -> str:
    dev, ho = d["dev"], d["holdout"]
    L = []
    L.append("=" * 100)
    L.append(f"STRATEGY  {d['id']}")
    L.append("=" * 100)
    L.append(f"family={d['family']}  timeframe={d['timeframe']}  direction={d['direction']}  "
             f"filters={d['filters']}  trend_mode={d['trend_mode']}  params={d['params']}")
    L.append(f"stop={d['stop']}   tp={d['tp']}   breakeven_after_tp1={d['breakeven_after_tp1']}"
             f"   trail_after_tp={d['trailing']}   entry={d['entry_mode']}")
    L.append("")
    L.append(f"{'':22}{'DEV COINS':>34}{'HOLDOUT COINS (unseen)':>34}")
    for k, label in [("trades", "trades"), ("ret_pct", "return %"), ("pf", "profit factor"),
                     ("expectancy_pct", "edge %/trade"), ("win_rate", "win rate %"),
                     ("max_dd", "max drawdown %"), ("sharpe", "sharpe"),
                     ("long_pct", "long P&L %"), ("short_pct", "short P&L %"),
                     ("tp1", "TP1 hit %"), ("tp2", "TP2 hit %"), ("tp3", "TP3 hit %"),
                     ("tp4", "TP4 hit %"), ("avg_bars", "avg bars held"),
                     ("max_consec_loss", "max consec losses")]:
        L.append(f"  {label:20}{str(dev.get(k, '-')):>34}{str(ho.get(k, '-')):>34}")
    L.append(f"  {'consistency':20}{d['dev_consistency']:>34}{d['holdout_consistency']:>34}")
    L.append("")
    L.append(f"SCORE  {d['score_explained']}")
    L.append("")
    L.append("REGIME BREAKDOWN (dev, P&L % by trend state at entry):")
    for k, v in d["dev_regime_pnl"].items():
        L.append(f"   {k:16} {v['pct']:+8.2f}%   ({v['n']} trades)")
    L.append("VOLATILITY STATE (dev):")
    for k, v in d["dev_vol_regime_pnl"].items():
        L.append(f"   {k:16} {v['pct']:+8.2f}%   ({v['n']} trades)")
    L.append(f"BEST REGIME: {best_regime(d)}")
    L.append("")
    L.append("HALF-YEAR (dev):    " + "  ".join(f"{k}:{v:+.0f}" for k, v in d["dev_halfyears"].items()))
    L.append("HALF-YEAR (holdout):" + "  ".join(f"{k}:{v:+.0f}" for k, v in d["holdout_halfyears"].items()))
    L.append("")
    rb, cs = d["robustness"], d["cost_stress"]
    L.append(f"ROBUSTNESS: instability={rb['instability']}  "
             f"neighbours profitable={rb['neighbours_profitable']}/{rb['n']}  "
             f"neighbour returns={rb.get('neighbour_returns')}")
    L.append(f"COST STRESS (2x fees+slippage): {cs['ret_pct_2x_costs']:+.1f}%  "
             f"PF {cs['pf_2x_costs']}")
    L.append("")
    L.append("WHY DID THIS STRATEGY SURVIVE?")
    for x in why(d):
        L.append(f"   + {x}")
    L.append("CAVEATS / OVERFITTING RISK:")
    cv = caveats(d)
    for x in (cv or ["none flagged"]):
        L.append(f"   - {x}")
    return "\n".join(L)


def main(top=4):
    universe = load_universe(DEV_COINS)
    hold_u = load_universe(HOLDOUT_COINS)
    rank = json.loads((OUT / "full_rank_dev.json").read_text())
    live = [r for r in rank if not r["disq"]][:top]
    by_id = {c['id']: c for c in generate(short_modes=['sym','off','weakdn','tp_weakdn'])}
    txt = []
    for r in live:
        c = by_id.get(r["id"])
        if not c:
            continue
        d = card(c, universe, hold_u)
        json.dump(d, open(OUT / f"card_{abs(hash(d['id']))%10**8}.json", "w"),
                  indent=1, default=float)
        txt.append(render(d))
        print(txt[-1], flush=True)
    (OUT / "strategy_reports.txt").write_text("\n\n".join(txt), encoding="utf-8")


if __name__ == "__main__":
    main()
