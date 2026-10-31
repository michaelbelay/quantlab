r"""Run one registered family through the RULES.md gates.

    .venv\\Scripts\\python.exe -m quant.run_family F1 dev       # DEV grid -> selection -> leverage
    .venv\\Scripts\\python.exe -m quant.run_family F1 valid     # chosen config on the 280 unseen coins
    .venv\\Scripts\\python.exe -m quant.run_family F1 final     # one look at 2026-03-26 .. 09-25

Results: runs/<family>_<stage>.json. VALID and FINAL refuse to run unless the previous stage passed.
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np

from strategies.families import FAMILIES, grid, neighbours

from . import sim
from .metrics import summary
from .panel import load
from .fair import all_coins
from . import panel_pos
from .paths import RUNS

DEV_START, DEV_END = "2021-01-01", "2026-03-26"
FINAL_START, FINAL_END = "2026-03-26", "2026-09-26"
A1_DEV_END = "2024-07-01"          # Amendment A1 time split (ALL coins)
B_START, B_DEV_END, B_VALID_END = "2024-09-01", "2025-09-01", "2026-03-26"   # Protocol B
LEVERAGES = [1, 2, 3, 5]
TWINS = 200
TWINS_MAX = 2000            # escalation: a D6 result within 85..99.5 pct is re-measured with 2,000 twins
TWIN_GREY = (85.0, 99.5)    # (200 twins: SE of a pct near 95 is ~1.5 points - seed alone can flip the gate)


def key(c: dict) -> str:
    return f"k{c['k']}_lb{c['lookback_days']}d_ev{c['every'] * 8}h"


def one(p, fam, cfg, lev=1.0, cost_mult=1.0, start=0):
    vt = fam.get("vol_target")
    r = sim.run(p, fam["make"](cfg["lookback_days"]), cfg["k"], cfg["every"], lev=fam.get("lev_cap", lev) if vt else lev,
                cost_mult=cost_mult, start=start, vol_target=vt, stop=fam.get("stop"))
    return summary(r, start)


def dev_gates(m: dict, m2: dict, a1: bool = False, b: bool = False) -> dict:
    need, label = (3, "D5 >= 3 of 4 periods positive") if a1 else (4, "D5 >= 4 of 6 years positive")
    d5 = m["quarters_positive"] >= 3 if b else m["years_positive"] >= need
    if b:
        label = "D5 >= 3 of 4 quarters positive"
    return {"D1 profit": m["final"] > sim.START_EQUITY, "D2 profit at 2x costs": m2["final"] > sim.START_EQUITY,
            "D3 Sharpe >= 1.0": m["sharpe"] >= 1.0, "D4 max DD <= 35%": m["max_dd_pct"] <= 35, label: d5}


def twins(p, fam, cfg, start: int = 0, n: int = TWINS) -> list[float]:
    vt = fam.get("vol_target")
    mk = fam["twin_cfg"](cfg["lookback_days"]) if "twin_cfg" in fam else fam["twin"]
    return [sim.run(p, mk(s), cfg["k"], cfg["every"], lev=fam.get("lev_cap", 1.0) if vt else 1.0,
                    vol_target=vt, stop=fam.get("stop")).equity[-1] for s in range(start, start + n)]


def stage_dev(fid: str) -> dict:
    fam = FAMILIES[fid]
    a1 = fam.get("universe") == "all"
    b = fam.get("universe") == "pos"
    if b:
        p = panel_pos.load().window(B_START, B_DEV_END)
    else:
        p = all_coins().window(DEV_START, A1_DEV_END) if a1 else load("dev").window(DEV_START, DEV_END)
    rows = {}
    t0 = time.time()
    for cfg in grid(fam["grid"]):
        m, m2 = one(p, fam, cfg), one(p, fam, cfg, cost_mult=2.0)
        rows[key(cfg)] = {"cfg": cfg, "base": m, "x2": m2, "gates": dev_gates(m, m2, a1, b)}
        print(f"{key(cfg):<18} final {m['final']:>9.2f}  x2 {m2['final']:>9.2f}  Sharpe {m['sharpe']:>5.2f}  "
              f"DD {m['max_dd_pct']:>5.1f}%  yrs+ {m['years_positive']}  {'PASS D1-D5' if all(rows[key(cfg)]['gates'].values()) else ''}",
              flush=True)
    print(f"grid done in {time.time() - t0:.0f}s")
    # D6 random twins, per (k, every), only where a config passed D1-D5
    cache = {}
    for kk, row in rows.items():
        if all(row["gates"].values()):
            tk = (row["cfg"]["k"], row["cfg"]["every"], row["cfg"]["lookback_days"] if "twin_cfg" in fam else None)
            if tk not in cache:
                print(f"random twins for k={tk[0]} every={tk[1] * 8}h ...", flush=True)
                cache[tk] = twins(p, fam, row["cfg"])
            tw = np.array(cache[tk])
            pct = float((tw < row["base"]["final"]).mean() * 100)
            if TWIN_GREY[0] <= pct < TWIN_GREY[1] and len(tw) < TWINS_MAX:
                print(f"  D6 at p{pct:.1f} is in the grey zone -> {TWINS_MAX} twins", flush=True)
                cache[tk] = cache[tk] + twins(p, fam, row["cfg"], start=len(tw), n=TWINS_MAX - len(tw))
                tw = np.array(cache[tk])
            row["twin_n"] = int(len(tw))
            row["twin_pct"] = round(float((tw < row["base"]["final"]).mean() * 100), 1)
            row["twin_median"] = round(float(np.median(tw)), 2)
            row["gates"]["D6 beats 95% of random twins"] = row["twin_pct"] >= 95
        else:
            row["gates"]["D6 beats 95% of random twins"] = None
    passing = {kk: r for kk, r in rows.items() if all(v for v in r["gates"].values())}
    out = {"family": fid, "name": fam["name"], "stage": "dev", "period": [DEV_START, A1_DEV_END if a1 else DEV_END],
           "coins": len(p.coins), "grid": rows, "passing_D1_D6": sorted(passing)}
    if not passing:
        out["verdict"] = "FAIL at DEV - no config passes D1-D6"
        return out
    best = max(passing, key=lambda kk: passing[kk]["base"]["sharpe"])
    cfg = rows[best]["cfg"]
    nb = [key(c) for c in neighbours(fam["grid"], cfg)]
    share = sum(rows[n]["gates"]["D1 profit"] for n in nb) / len(nb)
    out["chosen"] = best
    out["D7 neighbours profitable"] = {"share": round(share, 2), "pass": share >= 0.75, "neighbours": nb}
    if share < 0.75:
        out["verdict"] = f"FAIL at DEV - D7 neighbours {share:.0%} < 75%"
        return out
    if fam.get("vol_target"):
        out["chosen_leverage"] = fam["lev_cap"]
        out["verdict"] = "PASS DEV"
        return out
    levs = {}
    for L in LEVERAGES:
        r = sim.run(p, FAMILIES[fid]["make"](cfg["lookback_days"]), cfg["k"], cfg["every"], lev=L, stop=fam.get("stop"))
        m = summary(r)
        peak = float(np.nanmax(r.equity))
        m["liq_loss_share_of_peak"] = round(r.liq_loss / peak, 3)
        m["ok"] = m["max_dd_pct"] <= 35 and m["liq_loss_share_of_peak"] < 0.10 and m["final"] > sim.START_EQUITY
        levs[L] = m
        print(f"  leverage {L}x: final {m['final']:.2f} DD {m['max_dd_pct']}% liq {m['liquidations']} ok={m['ok']}")
    ok = [L for L, m in levs.items() if m["ok"]]
    out["leverage"] = levs
    out["chosen_leverage"] = max(ok) if ok else None
    out["verdict"] = "PASS DEV" if ok else "FAIL at DEV - no leverage keeps DD <= 35%"
    return out


def stage_valid(fid: str) -> dict:
    dev = json.loads((RUNS / f"{fid}_dev.json").read_text(encoding="utf-8"))
    if dev.get("verdict") != "PASS DEV":
        raise SystemExit(f"{fid}: DEV did not pass ({dev.get('verdict')}) - VALID refused")
    fam, cfg, L = FAMILIES[fid], dev["grid"][dev["chosen"]]["cfg"], float(dev["chosen_leverage"])
    if fam.get("universe") == "pos":          # Protocol B: same coins, later time
        p = panel_pos.load().window(B_START, B_VALID_END)
        s0 = int(p.index.searchsorted(__import__("pandas").Timestamp(B_DEV_END, tz="UTC")))
    elif fam.get("universe") == "all":          # A1: same coins, later time
        p = all_coins().window(DEV_START, DEV_END)
        s0 = int(p.index.searchsorted(__import__("pandas").Timestamp(A1_DEV_END, tz="UTC")))
    else:
        p, s0 = load("oos").window(DEV_START, DEV_END), 0
    m, m2 = one(p, fam, cfg, L, start=s0), one(p, fam, cfg, L, 2.0, start=s0)
    g = {"V1 profit": m["final"] > sim.START_EQUITY, "V2 profit at 2x costs": m2["final"] > sim.START_EQUITY,
         "V3 Sharpe >= 0.7": m["sharpe"] >= 0.7, "V4 max DD <= 40%": m["max_dd_pct"] <= 40}
    return {"family": fid, "stage": "valid", "chosen": dev["chosen"], "leverage": L, "coins": len(p.coins),
            "base": m, "x2": m2, "gates": g, "verdict": "PASS VALID" if all(g.values()) else "FAIL at VALID"}


def stage_final(fid: str) -> dict:
    v = json.loads((RUNS / f"{fid}_valid.json").read_text(encoding="utf-8"))
    if v.get("verdict") != "PASS VALID":
        raise SystemExit(f"{fid}: VALID did not pass - FINAL refused")
    dev = json.loads((RUNS / f"{fid}_dev.json").read_text(encoding="utf-8"))
    fam, cfg, L = FAMILIES[fid], dev["grid"][dev["chosen"]]["cfg"], float(dev["chosen_leverage"])
    if fam.get("universe") == "pos":
        sets = (("desk coins", panel_pos.load()),)
    elif fam.get("universe") == "all":
        sets = (("all coins", all_coins()),)
    else:
        sets = (("dev coins", load("dev")), ("unseen coins", load("oos")))
    res = {}
    for name, p in sets:
        p = p.window(B_START if fam.get("universe") == "pos" else DEV_START, FINAL_END)   # earlier bars feed signals only
        s0 = int(p.index.searchsorted(__import__("pandas").Timestamp(FINAL_START, tz="UTC")))
        res[name] = one(p, fam, cfg, L, start=s0)
    g = {f"F profit ({n})": m["final"] > sim.START_EQUITY for n, m in res.items()}
    g.update({f"F max DD <= 20% ({n})": m["max_dd_pct"] <= 20 for n, m in res.items()})
    return {"family": fid, "stage": "final", "results": res, "gates": g,
            "verdict": "PASS FINAL" if all(g.values()) else "FAIL at FINAL"}


def main() -> int:
    fid, stage = sys.argv[1], sys.argv[2]
    RUNS.mkdir(exist_ok=True)
    out = {"dev": stage_dev, "valid": stage_valid, "final": stage_final}[stage](fid)
    (RUNS / f"{fid}_{stage}.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("\nVERDICT:", out["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
