"""Flush bounce in falling markets. Rules: research/PREREGISTRATION_2026-10-07_flush.md (frozen, do not edit).

  .venv\\Scripts\\python.exe research\\flush.py info    # fit-window numbers 2021-23 (information only)
  .venv\\Scripts\\python.exe research\\flush.py testA   # development coins 2024-01-01..2026-09-18
  .venv\\Scripts\\python.exe research\\flush.py testB   # 280 unseen coins (only rules that passed A)
Trade mechanics are imported unchanged from downtrend.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import downtrend as D  # noqa: E402
from regime_switch import market_types  # noqa: E402

OUT = HERE / "flush"
D.RULES.update({
    "F1": ("capitulation", 1, 24, 1.5, {}),
    "F2": ("breakdown", 1, 24, 1.5, {"vol": True}),
    "F3": ("fund_lo", 1, 24, 1.5, {}),
})
RULES = ["F1", "F2", "F3"]


def info():
    OUT.mkdir(exist_ok=True)
    types = market_types()
    U = D.Universe(D.dev_files())
    res = {}
    for r in RULES:
        res[r] = {"DN": D.stats(D.run_rule(U, r, types, "DN", *D.FIT), D.FIT_HALVES),
                  "UP": D.stats(D.run_rule(U, r, types, "UP", *D.FIT), D.FIT_HALVES)}
        s = res[r]["DN"]
        print(f"{r} fit DN: n={s['trades']} pf={s['pf'] and round(s['pf'], 3)} t={s['day_t'] and round(s['day_t'], 2)}", flush=True)
    (OUT / "fit_info.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


def test(scope):
    OUT.mkdir(exist_ok=True)
    if scope == "B":
        a = json.loads((OUT / "testA.json").read_text(encoding="utf-8"))
        rules = [r for r, v in a.items() if v["pass"]]
        if not rules:
            print("no rule passed test A: test B is not run"); return
    else:
        rules = RULES
    types = market_types()
    U = D.Universe(D.dev_files() if scope == "A" else D.oos_files())
    end = D.TEST[1] if scope == "A" else "2026-09-01"
    years = D.TEST_YEARS if scope == "A" else D.TEST_YEARS[:2] + [("2026-01-01", "2026-09-01")]
    out = {}
    for r in rules:
        tr = D.run_rule(U, r, types, "DN", D.TEST[0], end)
        s = D.stats(tr, years)
        s["same_rule_UP_days"] = D.stats(D.run_rule(U, r, types, "UP", D.TEST[0], end), years)
        s["random_pct"], s["random_median"] = D.random_pct(U, tr, r, types) if len(tr) else (None, None)
        chk = {"A1 PF>=1.10 & PF2x>=1.00": (s["pf"] or 0) >= 1.10 and (s["pf_2x"] or 0) >= 1.00,
               "A2 day t>=2": (s["day_t"] or 0) >= 2.0,
               "A3 >=2/3 periods positive": sum(v["net"] > 0 for v in s["periods"].values()) >= 2,
               "A4 random >= p95": (s["random_pct"] or 0) >= 95,
               "A5 >=100 trades": s["trades"] >= 100}
        s["checks"], s["pass"] = chk, all(chk.values())
        out[r] = s
        tr.to_parquet(OUT / f"test{scope}_{r}.parquet")
        print(f"{r}: n={s['trades']} pf={s['pf'] and round(s['pf'], 3)} pf2x={s['pf_2x'] and round(s['pf_2x'], 3)} "
              f"t={s['day_t'] and round(s['day_t'], 2)} periods={ {k: round(v['net']) for k, v in s['periods'].items()} } "
              f"random_pct={s['random_pct']} -> {'PASS' if s['pass'] else 'FAIL'}", flush=True)
    (OUT / f"test{scope}.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    {"info": info, "testA": lambda: test("A"), "testB": lambda: test("B")}[sys.argv[1]]()
