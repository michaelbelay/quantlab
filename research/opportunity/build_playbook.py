"""Opportunity engine - build the casebook and the playbook from dev-coin history.

For every condition in common.CONDITIONS:
  1. find every past trigger on the 133 dev coins (1h futures, 2021 -> data end)
  2. FIT window (< 2025-01-01): choose direction + time limit, set the target
     (median favourable move) and stop (80th pct adverse move of winners) by a
     fixed rule - 6 choices per condition, no grid search
  3. TEST window (>= 2025-01-01): run the frozen rule, never seen by the fit
  4. compare with random entries (same coins, same window, same bracket)
  5. badge it with the pre-stated rule in badge()

The 280 unseen OOS coins and the sealed desk quadrant are NOT read here.

Run:  .venv\\Scripts\\python.exe research\\opportunity\\build_playbook.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from common import (CONDITIONS, COST_RT, FIT_END, HORIZONS, REGIMES, compute_conditions,
                    paths, regular_grid, simulate, triggers)

ROOT = Path(__file__).resolve().parents[2]
FUT = ROOT / "data" / "market" / "dev_1h" / "binance" / "futures"
OUT = Path(__file__).parent
RANDOM_PER_COIN = 300
rng = np.random.default_rng(20261006)


def dev_coins() -> list[str]:
    s = json.loads((ROOT / "data" / "market" / "universe" / "split_140.json").read_text(encoding="utf-8"))
    coins = list(dict.fromkeys(s["dev"] + s["holdout"]))
    have = [c for c in coins if (FUT / f"{c}_USDT_USDT-1h-futures.feather").exists()]
    missing = sorted(set(coins) - set(have))
    return have, missing


def collect():
    coins, missing = dev_coins()
    print(f"dev coins with data: {len(coins)}  unavailable: {missing}", flush=True)
    bucket = {k: [] for k in list(CONDITIONS) + ["_RANDOM"]}
    for n, coin in enumerate(coins, 1):
        df = pd.read_feather(FUT / f"{coin}_USDT_USDT-1h-futures.feather")
        fp = FUT / f"{coin}_USDT_USDT-1h-funding_rate.feather"
        fund = pd.read_feather(fp) if fp.exists() else None
        x = compute_conditions(regular_grid(df), fund)
        sig = x["sigma24"].to_numpy()
        dates = x["date"].dt.tz_localize(None).to_numpy()
        for name in list(CONDITIONS) + ["_RANDOM"]:
            if name == "_RANDOM":
                ok = np.flatnonzero(~np.isnan(sig) & (x["volume"].to_numpy() > 0))
                idx = np.sort(rng.choice(ok, size=min(RANDOM_PER_COIN, len(ok)), replace=False)) if len(ok) else ok
            else:
                idx = triggers(x[name])
            idx, P = paths(x, idx)
            if P is None:
                continue
            bucket[name].append({"coin": np.full(len(idx), coin), "date": dates[idx + 1],
                                 "sigma": sig[idx].astype(np.float64), **P})
        if n % 20 == 0:
            print(f"  {n}/{len(coins)} coins", flush=True)
    merged = {}
    for k, parts in bucket.items():
        if parts:
            merged[k] = {f: np.concatenate([p[f] for p in parts]) for f in parts[0]}
    return merged, coins, missing


def sub(E: dict, mask: np.ndarray) -> dict:
    return {k: v[mask] for k, v in E.items()}


def fit_rule(E: dict):
    """Fixed rule: for each (direction, horizon): target = median favourable
    excursion, stop = 80th pct adverse excursion of trades that ended in profit.
    Keep the (direction, horizon) with the best average net on the fit window."""
    best = None
    s = E["sigma"]
    for d in (1, -1):
        for H in HORIZONS:
            fav = (E["hi"][:, :H].max(1) if d == 1 else -E["lo"][:, :H].min(1)) / s
            adv = (-E["lo"][:, :H].min(1) if d == 1 else E["hi"][:, :H].max(1)) / s
            final = d * E["cl"][:, H - 1] / s
            tgt = float(max(np.median(fav), 0.3))
            winners = adv[final > 0]
            stp = float(max(np.percentile(winners, 80) if len(winners) >= 10 else 1.0, 0.3))
            net, _, _ = simulate(E, s, d, H, tgt, stp)
            m = float(net.mean())
            if best is None or m > best["fit_avg"]:
                best = {"dir": d, "H": H, "tgt": round(tgt, 3), "stp": round(stp, 3), "fit_avg": m}
    return best


def stats(E: dict, rule: dict) -> dict:
    n = len(E["sigma"])
    if n == 0:
        return {"n": 0}
    net, out, _ = simulate(E, E["sigma"], rule["dir"], rule["H"], rule["tgt"], rule["stp"])
    day = pd.to_datetime(E["date"]).floor("D")
    daily = pd.Series(net).groupby(day).mean()
    t_day = float(daily.mean() / daily.std(ddof=1) * np.sqrt(len(daily))) if len(daily) > 2 and daily.std() > 0 else 0.0
    wins, losses = net[net > 0].sum(), -net[net < 0].sum()
    return {
        "n": int(n), "coins": int(len(set(E["coin"]))), "days": int(len(daily)),
        "target_first": round(float((out == 1).mean()) * 100, 1),
        "stop_first": round(float((out == -1).mean()) * 100, 1),
        "time_exit": round(float((out == 0).mean()) * 100, 1),
        "avg_net_pct": round(float(net.mean()) * 100, 3),
        "median_net_pct": round(float(np.median(net)) * 100, 3),
        "pf": round(float(wins / losses), 3) if losses > 0 else None,
        "t_day": round(t_day, 2),
        "win_pct": round(float((net > 0).mean()) * 100, 1),
        "worst_pct": round(float(net.min()) * 100, 2),
    }


def window(E: dict, start=None, end=None) -> np.ndarray:
    d = E["date"].astype("datetime64[s]")          # naive UTC from .to_numpy()
    m = np.ones(len(d), dtype=bool)
    if start:
        m &= d >= np.datetime64(start)
    if end:
        m &= d < np.datetime64(end)
    return m


def badge(fit: dict, test: dict, base_test: dict, regimes_pos: int) -> tuple[str, list[str]]:
    """Pre-stated rule (written before results were seen).
    RED    : fit avg <= 0, or test avg <= 0, or test n < 30
    ORANGE : positive in both, but fails one of the YELLOW checks
    YELLOW : test t_day >= 2, test beats random entries by >= 0.10 pp, >= 3 of 4 regimes positive
    GREEN  : never from this engine - needs the pre-registered unseen-coin test + forward test."""
    why = []
    if fit.get("n", 0) == 0 or fit["avg_net_pct"] <= 0:
        why.append("loses on fit window")
    if test.get("n", 0) < 30:
        why.append(f"too few test cases ({test.get('n', 0)})")
    elif test["avg_net_pct"] <= 0:
        why.append("loses on test window 2025-26")
    if why:
        return "RED", why
    if test["t_day"] < 2:
        why.append(f"test t_day {test['t_day']} < 2")
    edge = test["avg_net_pct"] - base_test["avg_net_pct"]
    if edge < 0.10:
        why.append(f"beats random entries by only {edge:.2f} pp")
    if regimes_pos < 3:
        why.append(f"positive in {regimes_pos}/4 regimes")
    return ("ORANGE", why) if why else ("YELLOW", ["passes all dev checks; unseen-coin test not run yet"])


def main():
    t0 = time.time()
    data, coins, missing = collect()
    R = data["_RANDOM"]
    playbook = {"built": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
                "history": "133 dev coins (split_140 dev+holdout), 1h futures + funding",
                "coins_used": len(coins), "unavailable": missing,
                "fit_window": f"< {FIT_END}", "test_window": f">= {FIT_END}",
                "cost_round_trip_pct": COST_RT * 100, "trials": 6 * len(CONDITIONS),
                "conditions": {}}
    rows = []
    for name, desc in CONDITIONS.items():
        if name not in data:
            continue
        E = data[name]
        fitE, testE = sub(E, window(E, end=FIT_END)), sub(E, window(E, start=FIT_END))
        if len(fitE["sigma"]) < 30:
            continue
        rule = fit_rule(fitE)
        fit, test = stats(fitE, rule), stats(testE, rule)
        base_test = stats(sub(R, window(R, start=FIT_END)), rule)
        base_fit = stats(sub(R, window(R, end=FIT_END)), rule)
        reg = {}
        for rn, a, b in REGIMES:
            reg[rn] = stats(sub(E, window(E, a, b)), rule)
        rpos = sum(1 for v in reg.values() if v.get("n", 0) >= 10 and v["avg_net_pct"] > 0)
        b, why = badge(fit, test, base_test, rpos)
        playbook["conditions"][name] = {
            "description": desc, "direction": "LONG" if rule["dir"] == 1 else "SHORT",
            "hours": rule["H"], "target_sigma": rule["tgt"], "stop_sigma": rule["stp"],
            "fit": fit, "test": test, "random_fit": base_fit, "random_test": base_test,
            "regimes": reg, "regimes_positive": rpos, "badge": b, "badge_why": why,
        }
        rows.append([name, "LONG" if rule["dir"] == 1 else "SHORT", rule["H"], rule["tgt"], rule["stp"],
                     fit["n"], fit["avg_net_pct"], test["n"], test["avg_net_pct"], test["target_first"],
                     test["stop_first"], test["t_day"], base_test["avg_net_pct"], rpos, b])
        print(f"{name:12s} {rows[-1][1]:5s} {rule['H']:>2}h tgt {rule['tgt']:.2f}s stp {rule['stp']:.2f}s | "
              f"fit n={fit['n']:5d} avg {fit['avg_net_pct']:+.3f}% | test n={test['n']:5d} avg {test['avg_net_pct']:+.3f}% "
              f"t {test['t_day']:+.2f} rand {base_test['avg_net_pct']:+.3f}% | reg {rpos}/4 -> {b}", flush=True)
    (OUT / "playbook.json").write_text(json.dumps(playbook, indent=2), encoding="utf-8")
    pd.DataFrame(rows, columns=["condition", "dir", "hours", "tgt_sigma", "stp_sigma", "fit_n", "fit_avg_pct",
                                "test_n", "test_avg_pct", "test_target_first", "test_stop_first", "test_t_day",
                                "random_test_avg_pct", "regimes_pos", "badge"]
                 ).to_csv(OUT / "playbook_summary.csv", index=False)
    print(f"done in {time.time() - t0:.0f}s -> playbook.json, playbook_summary.csv")


if __name__ == "__main__":
    main()
