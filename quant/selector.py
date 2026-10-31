r"""F18: walk-forward selection among all registered family configs (FAMILIES.md).

    .venv\Scripts\python.exe -m quant.selector curves     # simulate every candidate once, cache curves
    .venv\Scripts\python.exe -m quant.selector run        # quarterly selection, gates on 2024-07 .. 2026-03
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from strategies.families import FAMILIES, grid

from . import sim
from .fair import all_coins
from .paths import DATA, RUNS

START, END = "2021-01-01", "2026-03-26"
LOOKBACK_D, MIN_SHARPE, SWITCH_COST = 365, 0.5, 0.002


def candidates():
    for fid, fam in FAMILIES.items():
        for cfg in grid(fam["grid"]):
            yield f"{fid}|k{cfg['k']}|lb{cfg['lookback_days']}|ev{cfg['every']}", fid, fam, cfg


def curves() -> None:
    p = all_coins().window(START, END)
    out = {}
    for i, (name, fid, fam, cfg) in enumerate(candidates(), 1):
        vt = fam.get("vol_target")
        r = sim.run(p, fam["make"](cfg["lookback_days"]), cfg["k"], cfg["every"],
                    lev=fam.get("lev_cap", 1.0) if vt else 1.0, vol_target=vt, stop=fam.get("stop"))
        out[name] = r.equity
        if i % 25 == 0:
            print(f"  {i} candidates", flush=True)
    np.savez_compressed(DATA / "selector_curves.npz", dates=p.dates, names=np.array(list(out)),
                        eq=np.column_stack(list(out.values())))
    print(f"cached {len(out)} candidate curves")


def final() -> dict:
    """FINAL: identical rule, curves extended to 2026-09-25; scored on 2026-03-26 .. 2026-09-25 only."""
    prev = json.loads((RUNS / "F18_valid.json").read_text(encoding="utf-8"))
    if prev["verdict"] != "PASS VALID":
        raise SystemExit("F18 VALID did not pass - FINAL refused")
    end, cache = "2026-09-26", DATA / "selector_curves_final.npz"
    if not cache.exists():
        p = all_coins().window(START, end)
        out = {}
        for i, (name, fid, fam, cfg) in enumerate(candidates(), 1):
            vt = fam.get("vol_target")
            r = sim.run(p, fam["make"](cfg["lookback_days"]), cfg["k"], cfg["every"],
                        lev=fam.get("lev_cap", 1.0) if vt else 1.0, vol_target=vt, stop=fam.get("stop"))
            out[name] = r.equity
            if i % 40 == 0:
                print(f"  {i} candidates", flush=True)
        np.savez_compressed(cache, dates=p.dates, names=np.array(list(out)), eq=np.column_stack(list(out.values())))
    res = run(end=end, cache=cache, score=("2026-03-26", end))
    g = {"profit": res["valid"]["final"] > 300, "max DD <= 20%": res["valid"]["max_dd_pct"] <= 20}
    res.update({"stage": "final", "final": res.pop("valid"), "final_x2": res.pop("valid_x2"), "gates": g,
                "verdict": "PASS FINAL" if all(g.values()) else "FAIL at FINAL"})
    return res


def run(end: str = END, cache=None, score: tuple | None = None) -> dict:
    z = np.load(cache or DATA / "selector_curves.npz")
    END_ = end
    idx = pd.to_datetime(z["dates"], utc=True)
    eq = pd.DataFrame(z["eq"], index=idx, columns=list(z["names"])).ffill()
    ret = eq.pct_change().fillna(0.0).where(eq.shift() > 0, 0.0)          # dead curve -> no return
    quarters = pd.date_range("2022-01-01", END_, freq="QS", tz="UTC")
    rows, chosen_prev = [], None
    equity = {1.0: [300.0], 2.0: [300.0]}
    series = {1.0: [], 2.0: []}
    for qs, qe in zip(quarters, list(quarters[1:]) + [pd.Timestamp(END_, tz="UTC")]):
        past = ret[(ret.index >= qs - pd.Timedelta(days=LOOKBACK_D)) & (ret.index < qs)]
        sd = past.std()
        sharpe = (past.mean() / sd.where(sd > 0) * np.sqrt(3 * 365)).dropna()
        best = sharpe.idxmax() if len(sharpe) else None
        pick = best if best is not None and sharpe[best] >= MIN_SHARPE else None
        fut = ret[(ret.index >= qs) & (ret.index < qe)]
        r = fut[pick] if pick else pd.Series(0.0, index=fut.index)
        for cm in (1.0, 2.0):
            e = equity[cm][-1]
            if pick != chosen_prev and (pick or chosen_prev):
                e *= 1 - SWITCH_COST * cm
            path = e * (1 + r).cumprod()
            series[cm].append(path)
            equity[cm].append(float(path.iloc[-1]) if len(path) else e)
        rows.append({"quarter": str(qs.date()), "pick": pick, "trailing_sharpe": round(float(sharpe[best]), 2) if best else None,
                     "quarter_return_pct": round(float((1 + r).prod() - 1) * 100, 1)})
        chosen_prev = pick
    res = {}
    for cm in (1.0, 2.0):
        s = pd.concat(series[cm])
        res[cm] = s
    def stats(s: pd.Series, a: str, b: str) -> dict:
        w = s[(s.index >= pd.Timestamp(a, tz="UTC")) & (s.index < pd.Timestamp(b, tz="UTC"))]
        w = w / w.iloc[0] * 300
        d = w.resample("1D").last().pct_change().dropna()
        yrs = (w.index[-1] - w.index[0]).days / 365.25
        return {"final": round(float(w.iloc[-1]), 2), "cagr_pct": round(((w.iloc[-1] / 300) ** (1 / yrs) - 1) * 100, 1),
                "sharpe": round(float(d.mean() / d.std() * np.sqrt(365)), 2) if d.std() > 0 else 0.0,
                "max_dd_pct": round(float((1 - w / w.cummax()).max()) * 100, 1)}
    early = stats(res[1.0], "2022-01-01", "2024-07-01")
    a, b = score or ("2024-07-01", END_)
    v1, v2 = stats(res[1.0], a, b), stats(res[2.0], a, b)
    g = {"profit": v1["final"] > 300, "profit with 2x switch cost": v2["final"] > 300,
         "Sharpe >= 0.7": v1["sharpe"] >= 0.7, "max DD <= 40%": v1["max_dd_pct"] <= 40}
    return {"family": "F18", "quarters": rows, "info_2022_2024H1": early, "valid": v1, "valid_x2": v2,
            "gates": g, "verdict": "PASS VALID" if all(g.values()) else "FAIL at VALID"}


def main() -> int:
    if sys.argv[1] == "curves":
        curves()
        return 0
    if sys.argv[1] == "final":
        out = final()
        (RUNS / "F18_final.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
        for r in out["quarters"][-3:]:
            print(r)
        print("FINAL 2026-03-26..09-25:", out["final"], "\n  2x switch:", out["final_x2"])
        print(out["gates"], "\nVERDICT:", out["verdict"])
        return 0
    out = run()
    (RUNS / "F18_valid.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    for r in out["quarters"]:
        print(r)
    print("2022-2024H1 (info):", out["info_2022_2024H1"])
    print("VALID 2024-07..2026-03:", out["valid"], "\n  2x switch:", out["valid_x2"])
    print(out["gates"], "\nVERDICT:", out["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
