r"""Trial counter for the whole project (Gap 2 item 3 of the 2026-10-09 assessment).

    .venv\Scripts\python.exe -m quant.trials          # -> runs/trials.json + printed summary

Counts every strategy configuration that was evaluated on data, removes exact duplicates, and estimates an
EFFECTIVE number of independent trials from the correlation of their return series (participation ratio of the
eigenvalues: N_eff = (sum l)^2 / sum l^2). N_eff is an estimate, not a law: it is the input to deflated-Sharpe /
expected-max-t corrections, where the raw count overstates and 1 understates.

Sources (all read-only):
  quantlab F-families  data/selector_curves.npz (every registered F config, 8h equity 2021-01..2026-03)
                       duplicates = identical equity curves
  quantlab Protocol C  runs/c_trades/<batch>/<tf>/*.parquet (every family x timeframe x batch)
                       duplicates = >= 95% identical (coin, side, entry time) sets on the same timeframe (e.g.
                       C30 = C29 + hedge); families with 0 trades never fired
                       F duplicates also include re-tests of one rule on another universe (F10 = F1, F11 = F8):
                       the selector cache holds them on the same ALL-coin universe, so their curves coincide
  quantlab one-offs    F18 selector, C39, C40 (1 each); Protocol B P1-P4 registered but never run (0);
                       DeepSeek's GridDCA sweep (6) and G1 / G2 (2 presets each), 2026-10-10/11
  research pipeline    research/pipeline/pipeline.db candidates; duplicates after normalising specs:
                       with trend_mode "both" the btc_regime / trend_align filters are no-ops (engine/signals.py)
  research legacy      research/registry/gates.yaml trials_offset (configs mined before the pipeline)
  incubator            research/incubator/incubator.db screens
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import defaultdict

import numpy as np
import pandas as pd

from .paths import DATA, RESEARCH, RUNS

C_END = pd.Timestamp("2026-03-26", tz="UTC")          # selection data ends here (later data is spent / not used)
NEAR_DUP = 0.95                                       # Protocol C: same timeframe, >= 95% identical entries


def n_eff(returns: np.ndarray) -> float:
    """Participation ratio of the correlation matrix of the columns (columns with zero variance dropped)."""
    x = returns[:, returns.std(axis=0) > 0]
    if x.shape[1] < 2:
        return float(x.shape[1])
    lam = np.clip(np.linalg.eigvalsh(np.corrcoef(x, rowvar=False)), 0, None)
    return float(lam.sum() ** 2 / (lam ** 2).sum())


def f_families() -> dict:
    z = np.load(DATA / "selector_curves.npz", allow_pickle=True)
    eq, names = z["eq"], [str(n) for n in z["names"]]
    keys = [hashlib.sha1(np.round(eq[:, j], 6).tobytes()).hexdigest() for j in range(eq.shape[1])]
    first = {}
    dups = []
    for n, k in zip(names, keys):
        if k in first:
            dups.append([n, first[k]])
        else:
            first[k] = n
    keep = [names.index(n) for n in first.values()]
    with np.errstate(all="ignore"):
        r = np.diff(np.log(np.clip(eq[:, keep], 1e-9, None)), axis=0)
    r = np.nan_to_num(r)
    per_family = defaultdict(int)
    for n in names:
        per_family[n.split("|")[0]] += 1
    return {"raw": len(names), "unique": len(keep), "duplicates": dups, "n_eff": round(n_eff(r), 1),
            "per_family": dict(per_family)}


def c_families() -> dict:
    sig = defaultdict(set)
    daily = defaultdict(lambda: defaultdict(float))
    counts = defaultdict(int)
    for f in sorted((RUNS / "c_trades").glob("*/*/*.parquet")):
        batch, tf = f.parent.parent.name, f.parent.name
        x = pd.read_parquet(f)
        if not len(x) or "family" not in x.columns:            # coin with no trades in this batch
            continue
        x["entry_t"] = pd.to_datetime(x["entry_t"], utc=True)
        x = x[x["entry_t"] < C_END]
        for fam, g in x.groupby("family"):
            key = (batch, tf, fam)
            g = g.sort_values(["entry_t", "side"])
            sig[key].update(zip([f.stem] * len(g), g["side"].tolist(), g["entry_t"].tolist()))
            counts[key] += len(g)
            for d, v in g.groupby(g["entry_t"].dt.floor("D"))["ret"].sum().items():
                daily[key][d] += v
    # every evaluated (batch, tf, family) from the ledger, including ones that never fired
    led = [json.loads(l) for l in open(RUNS / "ledger_c.jsonl", encoding="utf-8")]
    evaluated = sorted({(r["batch"], r["tf"], r["family"]) for r in led if r["stage"] == "dev"})
    never = [list(k) for k in evaluated if counts.get(k, 0) == 0]
    keep, dups = [], []
    for k in evaluated:                                  # near-duplicate: >= 95% identical entries (Jaccard)
        if counts.get(k, 0) == 0:
            continue
        twin = next((j for j in keep if j[1] == k[1] and
                     len(sig[k] & sig[j]) >= NEAR_DUP * len(sig[k] | sig[j])), None)
        if twin:
            dups.append([list(k), list(twin)])
        else:
            keep.append(k)
    days = sorted({d for k in keep for d in daily[k]})
    m = np.array([[daily[k].get(d, 0.0) for k in keep] for d in days]) if keep else np.zeros((0, 0))
    by_tf = {}
    for tf in ("1h", "30m", "15m"):
        cols = [i for i, k in enumerate(keep) if k[1] == tf]
        by_tf[tf] = {"unique": len(cols), "n_eff": round(n_eff(m[:, cols]), 1) if cols else 0}
    return {"raw_evaluated": len(evaluated), "never_fired": never, "unique": len(keep), "duplicates": dups,
            "n_eff": round(n_eff(m), 1) if len(keep) else 0, "by_tf": by_tf}


def _norm_spec(spec: dict) -> dict:
    s = dict(spec)
    filt = list(s.get("filters", []))
    if s.get("trend_mode") == "both":
        filt = [f for f in filt if f not in ("btc_regime", "trend_align")]
    if not any(f in ("btc_regime", "trend_align") for f in filt):
        s["trend_mode"] = None                            # trend_mode only acts through those two filters
    s["filters"] = sorted(filt)
    return s


def pipeline() -> dict:
    con = sqlite3.connect(f"file:{RESEARCH / 'pipeline' / 'pipeline.db'}?mode=ro", uri=True)
    rows = con.execute("select id, spec, cfg from candidates").fetchall()
    first, dups = {}, []
    for cid, s, c in rows:
        k = json.dumps(_norm_spec(json.loads(s)), sort_keys=True) + json.dumps(json.loads(c), sort_keys=True)
        if k in first:
            dups.append([cid, first[k]])
        else:
            first[k] = cid
    return {"raw": len(rows), "unique": len(first), "duplicates": len(dups), "duplicate_pairs": dups}


def legacy_offset() -> int:
    txt = (RESEARCH / "registry" / "gates.yaml").read_text(encoding="utf-8")
    return int(re.search(r"trials_offset:\s*(\d+)", txt).group(1))


def incubator_screens() -> int:
    con = sqlite3.connect(f"file:{RESEARCH / 'incubator' / 'incubator.db'}?mode=ro", uri=True)
    return int(con.execute("select count(*) from screens").fetchone()[0])


def expected_max_t(n: float) -> float:
    """Expected best t-statistic among n independent no-edge trials (Bailey & Lopez de Prado 2014:
    (1-g) * Z(1 - 1/n) + g * Z(1 - 1/(n e)), g = Euler-Mascheroni). sqrt(2 ln n) is only its upper bound."""
    if n <= 1:
        return 0.0
    from statistics import NormalDist
    z, g = NormalDist().inv_cdf, 0.5772156649
    return float((1 - g) * z(1 - 1 / n) + g * z(1 - 1 / (n * np.e)))


def main() -> None:
    f, c, p = f_families(), c_families(), pipeline()
    one_offs = {"F18 selector": 1, "C39": 1, "C40": 1, "Protocol B P1-P4 (never run)": 0,
                "DeepSeek GridDCA sweep (6 variants, 2026-10-10)": 6, "G1 GridDCA (2 presets)": 2,
                "G2 GridDCA + BTC trend (2 presets)": 2,
                "VBreak4 by market condition (4 cells, earlier research)": 4,
                "C44 wick follow (judged on VALID only, no dev stage row)": 1}
    leg, inc = legacy_offset(), incubator_screens()
    q_raw = f["raw"] + c["raw_evaluated"] + sum(one_offs.values())
    q_unique = f["unique"] + c["unique"] + sum(one_offs.values())
    q_eff = f["n_eff"] + c["n_eff"] + sum(one_offs.values())
    total_raw = leg + p["raw"] + q_raw + inc
    total_unique = leg + p["unique"] + q_unique + inc
    out = {"quantlab": {"F": f, "C": c, "one_offs": one_offs, "raw": q_raw, "unique": q_unique,
                        "n_eff_estimate": round(q_eff, 1),
                        "expected_best_t_of_noise": {"raw": round(expected_max_t(q_raw), 2),
                                                     "n_eff": round(expected_max_t(q_eff), 2)}},
           "research": {"legacy_offset": leg, "pipeline": p, "incubator_screens": inc},
           "project_total": {"raw": total_raw, "unique": total_unique,
                             "expected_best_t_of_noise": round(expected_max_t(total_unique), 2),
                             "note": "legacy offset is a recorded estimate, not de-duplicated; pipeline N_eff not "
                                     "computed (no stored return series per candidate)"}}
    (RUNS / "trials.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(f"quantlab F : raw {f['raw']}, unique {f['unique']}, N_eff {f['n_eff']}  per family {f['per_family']}")
    print(f"quantlab C : evaluated {c['raw_evaluated']}, never fired {len(c['never_fired'])}, duplicates "
          f"{len(c['duplicates'])}, unique {c['unique']}, N_eff {c['n_eff']}  by tf {c['by_tf']}")
    if c["duplicates"]:
        print("   C duplicates:", c["duplicates"])
    if c["never_fired"]:
        print("   C never fired:", c["never_fired"])
    print(f"quantlab   : raw {q_raw}, unique {q_unique}, N_eff ~{q_eff:.0f} -> expected best t of pure noise "
          f"{expected_max_t(q_raw):.2f} (raw) / {expected_max_t(q_eff):.2f} (N_eff)")
    print(f"pipeline   : raw {p['raw']}, unique {p['unique']} ({p['duplicates']} duplicates)")
    print(f"legacy     : {leg} (gates.yaml trials_offset)   incubator screens: {inc}")
    print(f"PROJECT    : raw {total_raw}, unique {total_unique} -> expected best t of noise "
          f"{expected_max_t(total_unique):.2f}")


if __name__ == "__main__":
    main()
