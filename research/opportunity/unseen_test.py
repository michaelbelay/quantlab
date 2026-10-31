"""Pre-registered test (PREREGISTRATION_2026-10-06_unseen.md): the frozen playbook on the 280 unseen coins.

Refuses to run if playbook.json or common.py differ from the registered sha256. Same cooldown, costs,
entry, same-bar rule and statistics as build_playbook.py. Random baseline: 300 entries per coin, seed 20261006.
Primary decision (VOLSPIKE_DN only): avg net > 0, beats random by >= 0.10 pp, day t >= 2.

Run:  .venv\\Scripts\\python.exe research\\opportunity\\unseen_test.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from common import compute_conditions, paths, regular_grid, triggers  # noqa: E402
from build_playbook import stats, sub, window  # noqa: E402

ROOT = HERE.parents[1]
OOS = ROOT / "data" / "market" / "extra_coins_1h"
FROZEN = {"playbook.json": "9ec9d590e9fe899f4320e130f29209d5c8e1296f22dc398ff3b53c39b38397aa",
          "common.py": "b96f2c0445b3d9feab7cce0f3a2cad4d0cd02a0bb444daf70c2c78c6006689c4"}


def main():
    for f, h in FROZEN.items():
        got = hashlib.sha256((HERE / f).read_bytes()).hexdigest()
        if got != h:
            raise SystemExit(f"{f} changed since registration ({got}) - test refused")
    book = json.loads((HERE / "playbook.json").read_text(encoding="utf-8"))
    rules = book["conditions"]
    kept = json.loads((ROOT / "research" / "pipeline" / "oos_universe.json").read_text(encoding="utf-8"))["kept"]
    rng = np.random.default_rng(20261006)
    t0 = time.time()
    bucket = {k: [] for k in list(rules) + ["_RANDOM"]}
    used, skipped = 0, []
    for n, sym in enumerate(kept, 1):
        d = OOS / sym
        if not (d / "ohlcv_1h.feather").exists():
            skipped.append(sym)
            continue
        df = pd.read_feather(d / "ohlcv_1h.feather")
        fund = pd.read_feather(d / "funding.feather") if (d / "funding.feather").exists() else None
        if len(df) < 800:
            skipped.append(sym)
            continue
        x = compute_conditions(regular_grid(df), fund)
        sig, vol = x["sigma24"].to_numpy(), x["volume"].to_numpy()
        dates = x["date"].dt.tz_localize(None).to_numpy()
        for name in list(rules) + ["_RANDOM"]:
            if name == "_RANDOM":
                ok = np.flatnonzero(~np.isnan(sig) & (vol > 0))
                idx = np.sort(rng.choice(ok, size=min(300, len(ok)), replace=False)) if len(ok) else ok
            else:
                idx = triggers(x[name])
            idx, P = paths(x, idx)
            if P is None:
                continue
            bucket[name].append({"coin": np.full(len(idx), sym), "date": dates[idx + 1],
                                 "sigma": sig[idx].astype(np.float64), **P})
        used += 1
        if n % 40 == 0:
            print(f"  {n}/{len(kept)} coins", flush=True)
    data = {k: {f: np.concatenate([p[f] for p in v]) for f in v[0]} for k, v in bucket.items() if v}
    R = data["_RANDOM"]
    out = {"run_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "coins_used": used,
           "skipped": skipped, "frozen": FROZEN, "conditions": {}}
    print(f"\n{'condition':12s} {'rule':10s} | {'dev test 25-26':>16s} | {'UNSEEN n':>8s} {'avg':>8s} {'median':>8s} {'day t':>6s} {'random':>7s} {'edge':>6s}")
    for name, r in rules.items():
        if name not in data:
            continue
        rule = {"dir": 1 if r["direction"] == "LONG" else -1, "H": r["hours"], "tgt": r["target_sigma"], "stp": r["stop_sigma"]}
        E = data[name]
        s_all, base = stats(E, rule), stats(R, rule)
        recent = stats(sub(E, window(E, start="2025-01-01")), rule)
        edge = s_all["avg_net_pct"] - base["avg_net_pct"]
        out["conditions"][name] = {"rule": rule, "dev_badge": r["badge"], "dev_test": r["test"], "unseen": s_all,
                                   "unseen_since_2025": recent, "unseen_random": base, "edge_pp": round(edge, 3)}
        print(f"{name:12s} {r['direction']:5s} {r['hours']:>2}h | {r['test']['avg_net_pct']:+7.3f}% t{r['test']['t_day']:+5.2f} | "
              f"{s_all['n']:8d} {s_all['avg_net_pct']:+7.3f}% {s_all['median_net_pct']:+7.3f}% {s_all['t_day']:+6.2f} "
              f"{base['avg_net_pct']:+6.3f}% {edge:+6.2f}")
    p = out["conditions"]["VOLSPIKE_DN"]
    g = {"avg net > 0": p["unseen"]["avg_net_pct"] > 0, "beats random by >= 0.10 pp": p["edge_pp"] >= 0.10,
         "day t >= 2": p["unseen"]["t_day"] >= 2}
    out["primary"] = {"condition": "VOLSPIKE_DN", "gates": g, "verdict": "PASS" if all(g.values()) else "FAIL"}
    (HERE / "unseen_results.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(f"\nPRIMARY VOLSPIKE_DN: {g} -> {out['primary']['verdict']}   ({used} coins, {time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
