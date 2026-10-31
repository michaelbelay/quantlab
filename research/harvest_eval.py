"""Staged screen for the families harvested from GreenAgent (2026-09-21).

Stage 1 (this pass) is deliberately cheap: each family is run against the
filter bank on the DEVELOPMENT coins only, one stop geometry, and scored with
the same metrics and consistency measure the tournament uses. Nothing here is
a verdict -- it decides which combinations are worth the expensive stages
(holdout coins, 2x costs, parameter neighbours, walk-forward).

Results append to research/harvest_ledger.jsonl one line at a time, so an
interrupted run resumes instead of restarting -- same contract as ledger.jsonl.

The gates mirror evaluate.py's, expressed against engine trades:
  * at least MIN_TRADES over the span (the anti-degenerate floor)
  * profitable at all
  * drawdown not absurd
  * profitable on more than one coin, and not dependent on a single coin
  * positive in at least a third of the half-year buckets
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "engine"))
from backtest import Config, simulate                            # noqa: E402
from features import DEV_COINS, load_universe                    # noqa: E402
from tournament import SPAN_YEARS, metrics, period_consistency   # noqa: E402

LEDGER = Path(__file__).resolve().parent / "harvest_ledger.jsonl"

FAMILIES = ["trend_resume", "rsi_reset", "band_fade_confirmed"]
FILTERSETS = [
    ([], "nofilt"),
    (["volume"], "vol"),
    (["btc_regime"], "btc"),
    (["btc_regime", "volume"], "btc+vol"),
    (["not_flat"], "notflat"),
]
STOP_ATR = 2.0
MIN_TRADES = 100 * SPAN_YEARS / 5.7   # keep the ~100/yr floor honest


def gate(m: dict, per_pair: pd.Series, buckets: dict) -> tuple[bool, list[str]]:
    reasons = []
    if m["trades"] < MIN_TRADES:
        reasons.append(f"too few trades ({m['trades']})")
    if m["ret_pct"] <= 0:
        reasons.append(f"not profitable ({m['ret_pct']:.1f}%)")
    if m["max_dd"] > 40:
        reasons.append(f"drawdown too deep ({m['max_dd']:.1f}%)")
    n_prof = int((per_pair > 0).sum())
    if n_prof <= 1:
        reasons.append(f"only {n_prof}/{len(per_pair)} coins profitable")
    elif per_pair.max() > 0 and per_pair.sum() > 0 and per_pair.max() / per_pair.sum() > 0.8:
        reasons.append("profit depends on a single coin")
    pos = sum(1 for v in buckets.values() if v > 0)
    if buckets and pos < len(buckets) / 3:
        reasons.append(f"positive in only {pos}/{len(buckets)} periods")
    return (not reasons), reasons


def done_keys() -> set:
    if not LEDGER.exists():
        return set()
    out = set()
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
            out.add((e["family"], e["filters"], e["direction"]))
        except Exception:
            pass
    return out


def main() -> None:
    uni = load_universe(DEV_COINS, futures=True)
    print(f"universe: {list(uni)}", flush=True)
    seen = done_keys()
    cfg = Config(leverage=1.0, stop_mode="atr", stop_atr=STOP_ATR,
                 tp_mode="none", tp_atr=(), tp_frac=(), entry_mode="instant")

    for fam in FAMILIES:
        for filts, fname in FILTERSETS:
            for direction in ("both", "long"):
                key = (fam, fname, direction)
                if key in seen:
                    continue
                spec = {"family": fam, "direction": direction, "filters": filts,
                        "trend_mode": "with", "params": {}}
                t0 = time.time()
                tr = simulate(uni, spec, cfg)
                if not tr:
                    rec = {"family": fam, "filters": fname, "direction": direction,
                           "status": "no_trades", "secs": round(time.time() - t0)}
                else:
                    m = metrics(tr)
                    cons, buckets = period_consistency(tr, uni)
                    df = pd.DataFrame([t.__dict__ for t in tr])
                    per_pair = df.groupby("pair")["pnl"].sum()
                    ok, reasons = gate(m, per_pair, buckets)
                    rec = {"family": fam, "filters": fname, "direction": direction,
                           "status": "pass" if ok else "reject",
                           "trades": int(m["trades"]),
                           "per_year": round(m["trades"] / SPAN_YEARS, 1),
                           "ret_pct": round(m["ret_pct"], 2),
                           "pf": round(m["pf"], 3),
                           "max_dd": round(m["max_dd"], 2),
                           "consistency": round(cons, 3),
                           "coins_profitable": int((per_pair > 0).sum()),
                           "coins": len(per_pair),
                           "buckets": {k: round(float(v), 2) for k, v in buckets.items()},
                           "reasons": reasons,
                           "secs": round(time.time() - t0)}
                with open(LEDGER, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, default=float) + "\n")
                print(f"{fam:22}{fname:9}{direction:6}{rec.get('status'):9}"
                      f"{rec.get('ret_pct', 0):>9}%  pf={rec.get('pf', 0):<6}"
                      f"tr={rec.get('trades', 0):<6}{';'.join(rec.get('reasons', []))[:60]}",
                      flush=True)
    print("HARVEST_SCREEN_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
