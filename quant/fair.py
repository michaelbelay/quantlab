r"""Amendment A1: re-run a DEV-passed family unchanged on ALL 413 coins (point in time).

    .venv\Scripts\python.exe -m quant.fair F9          # 2021-01-01 .. 2026-03-25, VALID gates
    .venv\Scripts\python.exe -m quant.fair F9 final    # 2026-03-26 .. 2026-09-25, one look (needs the first to pass)
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from strategies.families import FAMILIES

from . import sim
from .metrics import summary
from .panel import Panel, load
from .paths import RUNS


def all_coins() -> Panel:
    a, b = load("dev"), load("oos")
    assert (a.dates == b.dates).all()
    cat = lambda x, y: np.concatenate([x, y], axis=1)
    return Panel(a.dates, a.coins + b.coins, cat(a.close, b.close), cat(a.high, b.high), cat(a.low, b.low),
                 cat(a.qvol, b.qvol), cat(a.fund, b.fund), np.concatenate([a.min_notional, b.min_notional]))


def run(fid: str, stage: str) -> dict:
    dev = json.loads((RUNS / f"{fid}_dev.json").read_text(encoding="utf-8"))
    assert dev["verdict"] == "PASS DEV"
    fam, cfg, L = FAMILIES[fid], dev["grid"][dev["chosen"]]["cfg"], float(dev["chosen_leverage"])
    p = all_coins()
    if stage == "fair":
        p = p.window("2021-01-01", "2026-03-26")
        s0 = 0
    else:
        prev = json.loads((RUNS / f"{fid}_fair.json").read_text(encoding="utf-8"))
        if prev["verdict"] != "PASS FAIR":
            raise SystemExit("fair run did not pass - FINAL refused")
        p = p.window("2021-01-01", "2026-09-26")
        s0 = int(p.index.searchsorted(pd.Timestamp("2026-03-26", tz="UTC")))
    res = {}
    for name, cm in (("base", 1.0), ("x2", 2.0)):
        r = sim.run(p, fam["make"](cfg["lookback_days"]), cfg["k"], cfg["every"], lev=L, cost_mult=cm,
                    start=s0, vol_target=fam.get("vol_target"), stop=fam.get("stop"))
        res[name] = summary(r, s0)
    m, m2 = res["base"], res["x2"]
    if stage == "fair":
        g = {"profit": m["final"] > sim.START_EQUITY, "profit at 2x costs": m2["final"] > sim.START_EQUITY,
             "Sharpe >= 0.7": m["sharpe"] >= 0.7, "max DD <= 40%": m["max_dd_pct"] <= 40}
        verdict = "PASS FAIR" if all(g.values()) else "FAIL FAIR"
    else:
        g = {"profit": m["final"] > sim.START_EQUITY, "max DD <= 20%": m["max_dd_pct"] <= 20}
        verdict = "PASS FINAL" if all(g.values()) else "FAIL FINAL"
    return {"family": fid, "stage": stage, "config": dev["chosen"], "leverage": L, "coins": len(p.coins),
            "results": res, "gates": g, "verdict": verdict}


def main() -> int:
    fid = sys.argv[1]
    stage = sys.argv[2] if len(sys.argv) > 2 else "fair"
    out = run(fid, stage)
    (RUNS / f"{fid}_{stage}.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    for n, m in out["results"].items():
        print(n, {x: m[x] for x in ("final", "cagr_pct", "sharpe", "max_dd_pct", "years", "stops", "liquidations")})
    print(out["gates"], "\nVERDICT:", out["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
