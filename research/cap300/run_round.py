"""Run a CAP300 round: every design on the unseen coins (decisive) and the live universe (reference).

    .venv\\Scripts\\python.exe research\\cap300\\run_round.py --round 1 [--reps 200]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE), str(ROOT / "research" / "pipeline")]
import designs as DS  # noqa: E402
import sim as SM  # noqa: E402
import validate_daily as V  # noqa: E402

CLASS = {"G": "🟢 Validated", "Y": "🟡 Research lead", "O": "🟠 Weak signal", "R": "🔴 Rejected"}


def panels():
    btc = [("BTC", V.FUT / "BTC_USDT_USDT-1h-futures.feather", V.FUT / "BTC_USDT_USDT-1h-funding_rate.feather")]
    kept = json.loads((ROOT / "research" / "pipeline" / "oos_universe.json").read_text(encoding="utf-8"))["kept"]
    oos = [(s[:-4], V.OOS / s / "ohlcv_1h.feather", V.OOS / s / "funding.feather") for s in kept if (V.OOS / s / "ohlcv_1h.feather").exists()]
    cfg = json.loads((ROOT / "configs" / "live_coins_2026-10.json").read_text(encoding="utf-8"))
    wl = sorted({p.split("/")[0] for p in cfg["pair_whitelist"]} - {"BTC"})
    live = [(c, V.FUT / f"{c}_USDT_USDT-1h-futures.feather", V.FUT / f"{c}_USDT_USDT-1h-funding_rate.feather") for c in wl]
    live = [x for x in live if x[1].exists()]
    return {"unseen": V.build_panel(oos + btc), "live": V.build_panel(live + btc)}


def build(design, fn, kw, D, coins):
    if fn == "vt":
        return DS.vol_target(DS.liquid_trend(D, coins, **kw), D)
    return fn(D, coins, **kw)


def dsr(daily: pd.Series, n_trials: int, sr_var: float) -> float | None:
    x = daily.to_numpy()
    if len(x) < 60 or x.std() == 0:
        return None
    sr = x.mean() / x.std(ddof=1)
    z = (x - x.mean()) / x.std()
    sk, ku = float((z ** 3).mean()), float((z ** 4).mean())
    g = 0.5772156649
    N = NormalDist()
    sr0 = math.sqrt(sr_var) * ((1 - g) * N.inv_cdf(1 - 1 / n_trials) + g * N.inv_cdf(1 - 1 / (n_trials * math.e)))
    den = 1 - sk * sr + (ku - 1) / 4 * sr ** 2
    return float(N.cdf((sr - sr0) * math.sqrt(len(x) - 1) / math.sqrt(den))) if den > 0 else 0.0


def classify(m: dict) -> tuple[str, list[str]]:
    pos = sum(1 for k in ("reg_2021", "reg_2022", "reg_2023_24", "reg_2025_26") if m[k] > 0)
    folds = sum(1 for v in m["folds"].values() if v > 0)
    checks = [("PF >= 1.10", (m["pf"] or 0) >= 1.10), ("PF 2x costs >= 1.05", (m["pf_2x"] or 0) >= 1.05),
              ("max DD <= 40%", m["max_dd"] <= 0.40), (f"regimes >= 3/4 ({pos}/4)", pos >= 3),
              (f"random twin >= p95 (p{m['random_pct']:.0f})", m["random_pct"] >= 95), (f"folds >= 5/8 ({folds}/8)", folds >= 5)]
    fails = [n for n, ok in checks if not ok]
    if not fails:
        return "G", fails
    if (m["pf"] or 0) >= 1.10 and m["random_pct"] >= 90 and m["max_dd"] <= 0.50:
        return "Y", fails
    if (m["pf"] or 0) > 1.0 or m["random_pct"] >= 75:
        return "O", fails
    return "R", fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--reps", type=int, default=200)
    a = ap.parse_args()
    designs = getattr(DS, f"ROUND{a.round}")
    P = panels()
    minn = SM.min_notionals()
    rng = np.random.default_rng(20261004 + a.round)
    results = {"round": a.round, "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "rows": []}
    dailies = {}
    for name, fn, kw in designs:
        row = {"design": name, "params": {k: v for k, v in kw.items()}, "doc": ((fn.__doc__ if callable(fn) else DS.liquid_trend.__doc__) or "").strip()}
        for uni, D in P.items():
            coins = [c for c in D["close"].columns if c != "BTC"]
            W = build(name, fn, kw, D, coins).loc["2021-01-01":]
            r1 = SM.simulate(W, D, minn=minn)
            m = SM.metrics(r1)
            m2 = SM.metrics(SM.simulate(W, D, minn=minn, cost_mult=2.0))
            m["pf_2x"], m["final_2x"] = m2["pf"], m2["final"]
            reps = a.reps if uni == "unseen" else max(50, a.reps // 4)
            finals = np.array([SM.simulate(DS.random_twin(W, D, coins, kw.get("k", 30), rng), D, minn=minn)["equity"].iloc[-1]
                               for _ in range(reps)])
            m["random_pct"] = float((finals < m["final"]).mean() * 100)
            m["random_median_final"] = float(np.median(finals))
            dailies[(name, uni)] = m.pop("daily")
            row[uni] = m
        results["rows"].append(row)
        u = row["unseen"]
        print(f"{name:18} unseen: final {u['final']:7.1f} (2x {u['final_2x']:7.1f}) PF {u['pf'] or 0:.2f}/{u['pf_2x'] or 0:.2f} DD {u['max_dd']:.0%} "
              f"CAGR {u['cagr']:+.1%} rnd p{u['random_pct']:.0f} (median twin {u['random_median_final']:.0f}) pos {u['avg_positions']:.1f} "
              f"skipped {u['skipped_orders']} | live-universe final {row['live']['final']:.0f} DD {row['live']['max_dd']:.0%}", flush=True)
    srs = [d.mean() / d.std() for (n, u), d in dailies.items() if u == "unseen" and d.std() > 0]
    trials = 8000 + 400 + len(designs) * a.round
    for row in results["rows"]:
        u = row["unseen"]
        u["dsr"] = dsr(dailies[(row["design"], "unseen")], trials, float(np.var(srs, ddof=1)) if len(srs) > 2 else 1e-4)
        cls, fails = classify(u)
        row["class"], row["fails"] = cls, fails
    out = HERE / f"round{a.round}_results.json"
    out.write_text(json.dumps(results, indent=1, default=float), encoding="utf-8")
    print("\nCLASSIFICATION (unseen coins):")
    for row in sorted(results["rows"], key=lambda r: "GYOR".index(r["class"])):
        print(f"  {CLASS[row['class']]:18} {row['design']:18} {'; '.join(row['fails']) or 'all bars passed'}")
    print(f"ROUND{a.round}_COMPLETE")


if __name__ == "__main__":
    main()
