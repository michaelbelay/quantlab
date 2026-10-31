r"""Protocol C evaluation of generated trades (DEV unless told otherwise) -> runs/ledger_c.jsonl.

    .venv\Scripts\python.exe -m quant.eval_c dev   [--batch BATCH1]
    .venv\Scripts\python.exe -m quant.eval_c valid FAMILY TF [--batch BATCH1]   # only for a DEV pass
    .venv\Scripts\python.exe -m quant.eval_c wf FAMILY TF [--batch BATCH1]      # only for a VALID pass
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import trades as T
from .book import replay, metrics
from .paths import MIN_NOTIONAL, RUNS

PERIODS = {
    "1h": {"dev": [("2021", "2021-01-01", "2022-01-01"), ("2022", "2022-01-01", "2023-01-01"),
                   ("2023", "2023-01-01", "2024-01-01"), ("2024H1", "2024-01-01", "2024-07-01")],
           "valid": [("2024H2", "2024-07-01", "2025-01-01"), ("2025H1", "2025-01-01", "2025-07-01"),
                     ("2025H2", "2025-07-01", "2026-01-01"), ("2026Q1", "2026-01-01", "2026-03-26")]},
    "intra": {"dev": [("Q1", "2024-09-01", "2024-12-01"), ("Q2", "2024-12-01", "2025-03-01"),
                      ("Q3", "2025-03-01", "2025-06-01"), ("Q4", "2025-06-01", "2025-09-01")],
              "valid": [("Q5", "2025-09-01", "2025-12-01"), ("Q6", "2025-12-01", "2026-03-26")]},
}

# PROTOCOL_C "WALK-FORWARD" gate (implemented 2026-10-09; before that it was documented but not enforced).
# 1h: 8 half-years 2022H2 .. 2026H1, the last one cut at 2026-03-26 because data from then on is not used for
# selection (PROTOCOL_C "Splits"). 15m/30m: the last 4 quarters before 2026-03-26. A period counts as positive when
# the summed per-trade return of the family's trades entered in it is > 0 (same measure as run_c40.py).
WALK_FORWARD = {
    "1h": ([("2022H2", "2022-07-01", "2023-01-01"), ("2023H1", "2023-01-01", "2023-07-01"),
            ("2023H2", "2023-07-01", "2024-01-01"), ("2024H1", "2024-01-01", "2024-07-01"),
            ("2024H2", "2024-07-01", "2025-01-01"), ("2025H1", "2025-01-01", "2025-07-01"),
            ("2025H2", "2025-07-01", "2026-01-01"), ("2026H1*", "2026-01-01", "2026-03-26")], 5),
    "intra": ([("Q3", "2025-03-01", "2025-06-01"), ("Q4", "2025-06-01", "2025-09-01"),
               ("Q5", "2025-09-01", "2025-12-01"), ("Q6", "2025-12-01", "2026-03-26")], 3),
}


def walk_forward(t: pd.DataFrame, tf: str) -> dict:
    periods, need = WALK_FORWARD["1h" if tf == "1h" else "intra"]
    per = {}
    for name, a, b in periods:
        x = t[(t["entry_t"] >= pd.Timestamp(a, tz="UTC")) & (t["entry_t"] < pd.Timestamp(b, tz="UTC"))]
        per[name] = {"trades": int(len(x)), "sum_ret_pct": round(float(x["ret"].sum() * 100), 2)}
    pos = sum(v["sum_ret_pct"] > 0 for v in per.values())
    return {"periods": per, "positive": pos, "needed": need, "of": len(periods), "passed": pos >= need}


def mins() -> dict:
    rows = json.loads(MIN_NOTIONAL.read_text(encoding="utf-8"))["rows"]
    return {r["pair"].split("/")[0]: max(x for x in (r["cost_min"], r["notional_filter"], 5.0) if x is not None) for r in rows}


def load(batch: str, tf: str, a: str, b: str) -> tuple[pd.DataFrame, dict]:
    d = RUNS / "c_trades" / batch / tf
    parts, twins = [], {}
    lo, hi = pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC")
    for f in sorted(d.glob("*.parquet")):
        x = pd.read_parquet(f)
        if not len(x):
            continue
        for c in ("entry_t", "exit_t"):
            x[c] = pd.to_datetime(x[c], utc=True)
        x = x[(x["entry_t"] >= lo) & (x["entry_t"] < hi)]
        parts.append(x[["family", "coin", "side", "entry_t", "exit_t", "ret", "gross", "funding", "mae", "reason", "bars"]])
        tw = d / f"{f.stem}.twins.npz"
        if tw.exists():
            z = np.load(tw)
            for k in z.files:
                twins[k] = twins.get(k, 0) + z[k]
    return (pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()), twins


def evaluate(t: pd.DataFrame, periods, mn: dict, twin: np.ndarray | None) -> dict:
    out = {}
    t2 = t.copy()
    t2["ret"] = t2["ret"] - 2 * (T.FEE + T.SLIP) - np.where(t2["reason"] == "stop", T.STOP_EXTRA, 0.0)
    for name, kw in (("book", {}), ("balanced", {"balanced": True})):
        bt, curve = replay(t, mn, **kw)
        out[name] = metrics(bt, curve, periods)
    bt2, c2 = replay(t2, mn)
    out["book_x2"] = {k: v for k, v in metrics(bt2, c2, periods).items() if k in ("final", "pf", "max_dd_pct", "sharpe")}
    # PROTOCOL_C "Portfolio": 2x and 3x are reported, never gated (until 2026-10-09 no code path produced them)
    for lev in (2, 3):
        bl, cl = replay(t, mn, lev=lev)
        m = {k: v for k, v in metrics(bl, cl, periods).items() if k in ("final", "pf", "max_dd_pct", "sharpe")}
        m["liquidations"] = int((bl["taken"] & bl["liquidated"]).sum()) if len(bl) else 0
        out[f"book_lev{lev}"] = m
    raw_pf = t.loc[t["ret"] > 0, "ret"].sum() / max(1e-9, -t.loc[t["ret"] < 0, "ret"].sum())
    out["all_signals"] = {"trades": int(len(t)), "pf_per_trade": round(float(raw_pf), 3),
                          "mean_ret_pct": round(float(t["ret"].mean() * 100), 3)}
    if twin is not None:
        out["twin_pct"] = round(float((twin < t["ret"].sum()).mean() * 100), 1)
    return out


def dev_gates(r: dict) -> dict:
    m = r["book"]
    if m.get("trades", 0) == 0:
        return {"≥200 trades": False}
    return {"≥200 trades": m["trades"] >= 200, "PF ≥ 1.15": m["pf"] >= 1.15, "PF ≥ 1.0 at 2x costs": r["book_x2"]["pf"] >= 1.0,
            "DD ≤ 35%": m["max_dd_pct"] <= 35, "≥3 of 4 periods positive": m["periods_positive"] >= 3,
            "beats 95% of random twins": r.get("twin_pct", 0) >= 95,
            "top coin ≤ 20% of profit": (m["top_coin_share"] or 1) <= 0.20}


def ledger(row: dict) -> None:
    with open(RUNS / "ledger_c.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["dev", "valid", "wf"])
    ap.add_argument("family", nargs="?")
    ap.add_argument("tf", nargs="?")
    ap.add_argument("--batch", default="BATCH1")
    a = ap.parse_args()
    mn = mins()
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if a.stage == "dev":
        for tf in ("1h", "30m", "15m"):
            per = PERIODS["1h" if tf == "1h" else "intra"]["dev"]
            t, twins = load(a.batch, tf, per[0][1], per[-1][2])
            if "family" not in t:                    # batch has no trades on this timeframe (e.g. 15m-only BATCH6)
                continue
            for fid in sorted(t["family"].unique()):
                r = evaluate(t[t["family"] == fid].reset_index(drop=True), per, mn, twins.get(fid))
                g = dev_gates(r)
                verdict = "PASS DEV" if all(g.values()) else "FAIL DEV"
                ledger({"at": stamp, "batch": a.batch, "family": fid, "tf": tf, "stage": "dev", "result": r,
                        "gates": g, "verdict": verdict})
                m = r["book"]
                print(f"{tf:>3} {fid}  trades {m.get('trades', 0):>5}  PF {m.get('pf', 0):>5}  x2 {r['book_x2'].get('pf', 0):>5}  "
                      f"final {m.get('final', 0):>8}  DD {m.get('max_dd_pct', 0):>5}%  Sharpe {m.get('sharpe', 0):>5}  "
                      f"per {m.get('periods')}  L {m.get('long', {}).get('pf')} S {m.get('short', {}).get('pf')}  "
                      f"twin {r.get('twin_pct')}  bal {r['balanced'].get('final')}  {verdict}", flush=True)
        return 0
    rows = [json.loads(l) for l in open(RUNS / "ledger_c.jsonl", encoding="utf-8")]
    if a.stage == "wf":
        if not any(r["family"] == a.family and r["tf"] == a.tf and r["stage"] == "valid" and r["verdict"] == "PASS VALID"
                   for r in rows):
            raise SystemExit("no VALID pass recorded for this family/timeframe - WALK-FORWARD refused")
        periods = WALK_FORWARD["1h" if a.tf == "1h" else "intra"][0]
        t, _ = load(a.batch, a.tf, periods[0][1], periods[-1][2])
        w = walk_forward(t[t["family"] == a.family].reset_index(drop=True), a.tf)
        verdict = "PASS WALK-FORWARD" if w["passed"] else "FAIL WALK-FORWARD"
        ledger({"at": stamp, "batch": a.batch, "family": a.family, "tf": a.tf, "stage": "wf", "result": w,
                "gates": {f"≥{w['needed']} of {w['of']} periods positive": w["passed"]}, "verdict": verdict})
        print(json.dumps(w, indent=1))
        print("VERDICT:", verdict)
        return 0
    # valid: one family/timeframe that passed DEV
    ok = [r for r in rows if r["family"] == a.family and r["tf"] == a.tf and r["stage"] == "dev" and r["verdict"] == "PASS DEV"]
    if not ok:
        raise SystemExit("no DEV pass recorded for this family/timeframe - VALID refused")
    per = PERIODS["1h" if a.tf == "1h" else "intra"]["valid"]
    t, _ = load(a.batch, a.tf, per[0][1], per[-1][2])
    r = evaluate(t[t["family"] == a.family].reset_index(drop=True), per, mn, None)
    m = r["book"]
    g = {"PF ≥ 1.10": m["pf"] >= 1.10, "profit": m["final"] > 300, "profit at 2x costs": r["book_x2"]["final"] > 300,
         "DD ≤ 40%": m["max_dd_pct"] <= 40}
    verdict = "PASS VALID" if all(g.values()) else "FAIL VALID"
    ledger({"at": stamp, "batch": a.batch, "family": a.family, "tf": a.tf, "stage": "valid", "result": r, "gates": g,
            "verdict": verdict})
    print(json.dumps({"book": m, "x2": r["book_x2"], "balanced": r["balanced"].get("final"), "gates": g}, indent=1, default=str))
    print("VERDICT:", verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
