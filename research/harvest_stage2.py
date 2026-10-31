"""Stage 2 for the harvested families: the expensive tests, survivors only.

Stage 1 (harvest_eval.py) ranked family x filter x direction on the development
coins. This applies the three checks that have historically done the killing:

  * COIN HOLDOUT   -- re-run on eight coins that played no part in any decision
  * 2x COSTS       -- fees and slippage doubled, the test that "every strategy
                      killed earlier in this project died here"
  * PARAM NEIGHBOURS -- stop geometry nudged +-25%; a real edge degrades
                      gracefully, a curve-fit collapses

These families trade 330-400 times a year, far above the ~194/yr of the
existing delivered pick, so the cost test is the one to watch: churn is exactly
what doubling costs punishes.

Appends to harvest_stage2.jsonl, resumable.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "engine"))
import backtest as bt                                            # noqa: E402
from backtest import Config, simulate                            # noqa: E402
from features import DEV_COINS, HOLDOUT_COINS, load_universe     # noqa: E402
from tournament import SPAN_YEARS, metrics, period_consistency   # noqa: E402

STAGE1 = HERE / "harvest_ledger.jsonl"
OUT = HERE / "harvest_stage2.jsonl"
TOP_N = 6


def run(uni, spec, cfg):
    tr = simulate(uni, spec, cfg)
    if not tr:
        return None, None
    m = metrics(tr)
    cons, buckets = period_consistency(tr, uni)
    m["consistency"] = round(cons, 3)
    m["buckets"] = {k: round(float(v), 2) for k, v in buckets.items()}
    return m, tr


def main() -> None:
    rows = [json.loads(l) for l in STAGE1.read_text(encoding="utf-8").splitlines() if l.strip()]
    survivors = [r for r in rows if r.get("status") == "pass"]
    survivors.sort(key=lambda r: -r["ret_pct"])
    survivors = survivors[:TOP_N]

    done = set()
    if OUT.exists():
        for l in OUT.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(l)
                done.add((e["family"], e["filters"], e["direction"]))
            except Exception:
                pass

    dev = load_universe(DEV_COINS, futures=True)
    hold = load_universe(HOLDOUT_COINS, futures=True)
    print(f"dev={list(dev)}\nholdout={list(hold)}\n", flush=True)

    fmap = {"nofilt": [], "vol": ["volume"], "btc": ["btc_regime"],
            "btc+vol": ["btc_regime", "volume"], "notflat": ["not_flat"]}

    for s in survivors:
        key = (s["family"], s["filters"], s["direction"])
        if key in done:
            continue
        t0 = time.time()
        spec = {"family": s["family"], "direction": s["direction"],
                "filters": fmap[s["filters"]], "trend_mode": "with", "params": {}}
        rec = {"family": s["family"], "filters": s["filters"],
               "direction": s["direction"], "dev_ret": s["ret_pct"], "dev_pf": s["pf"]}

        # --- coin holdout ---
        hm, _ = run(hold, spec, Config(leverage=1.0, stop_mode="atr", stop_atr=2.0,
                                       tp_mode="none", tp_atr=(), tp_frac=(),
                                       entry_mode="instant"))
        if hm:
            rec.update(holdout_ret=round(hm["ret_pct"], 2), holdout_pf=round(hm["pf"], 3),
                       holdout_dd=round(hm["max_dd"], 2), holdout_trades=int(hm["trades"]),
                       holdout_consistency=hm["consistency"])

        # --- 2x costs, on dev ---
        old_fee, old_slip = bt.FEE, bt.SLIP
        bt.FEE, bt.SLIP = old_fee * 2, old_slip * 2
        try:
            cm, _ = run(dev, spec, Config(leverage=1.0, stop_mode="atr", stop_atr=2.0,
                                          tp_mode="none", tp_atr=(), tp_frac=(),
                                          entry_mode="instant"))
        finally:
            bt.FEE, bt.SLIP = old_fee, old_slip
        if cm:
            rec.update(ret_2x_costs=round(cm["ret_pct"], 2), pf_2x_costs=round(cm["pf"], 3),
                       trades_2x_costs=int(cm["trades"]))

        # --- parameter neighbours: stop +-25% ---
        neigh = []
        for stop in (1.5, 2.5):
            nm, _ = run(dev, spec, Config(leverage=1.0, stop_mode="atr", stop_atr=stop,
                                          tp_mode="none", tp_atr=(), tp_frac=(),
                                          entry_mode="instant"))
            neigh.append(round(nm["ret_pct"], 2) if nm else None)
        rec["neighbour_returns"] = neigh
        rec["neighbours_profitable"] = sum(1 for x in neigh if x and x > 0)
        rec["secs"] = round(time.time() - t0)

        with open(OUT, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=float) + "\n")
        print(f"{rec['family']:20}{rec['filters']:9}{rec['direction']:6} "
              f"dev={rec['dev_ret']:>8}  holdout={rec.get('holdout_ret'):>8} "
              f"(pf {rec.get('holdout_pf')})  2xcost={rec.get('ret_2x_costs'):>8} "
              f"(pf {rec.get('pf_2x_costs')})  neigh={neigh}", flush=True)
    print("STAGE2_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
