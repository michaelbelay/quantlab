"""Campaign research report from research/pipeline/pipeline.db (read-only).

    .venv\\Scripts\\python.exe research\\pipeline\\report.py --batches 4-13 --out <file.md>

Every number is computed from the stored metrics, gates and trade files; nothing is typed in.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics as stt
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
NEW_FAMILIES = {"funding_extreme", "structure_break", "rel_strength", "regime_switch", "combo"}
STAGE_ORDER = ["G1", "G2", "G3", "diversity", "G4", "G5"]


def load(batches: list[int]):
    con = sqlite3.connect(f"file:{HERE / 'pipeline.db'}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    q = ",".join("?" * len(batches))
    cands = [dict(r) for r in con.execute(f"SELECT * FROM candidates WHERE batch IN ({q}) AND id != 'calibration-vbreak4both'", batches)]
    ids = [c["id"] for c in cands]
    met, gts = defaultdict(dict), defaultdict(dict)
    for r in con.execute("SELECT * FROM metrics"):
        if r["id"] in ids or r["id"] == "calibration-vbreak4both":
            met[r["id"]][r["scope"]] = json.loads(r["data"])
    for r in con.execute("SELECT * FROM gates"):
        if r["id"] in ids or r["id"] == "calibration-vbreak4both":
            gts[r["id"]][r["gate"]] = (r["result"], r["value"])
    bat = [dict(r) for r in con.execute(f"SELECT * FROM batches WHERE id IN ({q})", batches)]
    con.close()
    for c in cands:
        c["spec"], c["cfg"] = json.loads(c["spec"]), json.loads(c["cfg"])
        c["m"], c["g"] = met[c["id"]], gts[c["id"]]
        c["dev"] = c["m"].get("dev", {})
        c["dev2"] = c["m"].get("dev 2x costs", {})
        c["oos"] = c["m"].get("out-of-sample", {})
    cal = {"m": met.get("calibration-vbreak4both", {}), "g": gts.get("calibration-vbreak4both", {})}
    return cands, bat, cal


def f(x, d=2):
    return "—" if x is None else (f"{x:.{d}f}" if isinstance(x, (int, float)) else str(x))


def med(xs):
    xs = [x for x in xs if x is not None]
    return stt.median(xs) if xs else None


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def side_split(cid: str):
    p = HERE / "trades" / f"{cid}__dev.parquet"
    if not p.exists():
        return None
    d = pd.read_parquet(p, columns=["side", "pnl"])
    g = d.groupby("side").pnl.agg(["count", "sum"])
    out = {}
    for s in ("long", "short"):
        if s in g.index:
            sub = d[d.side == s].pnl
            w, l = sub[sub > 0].sum(), -sub[sub < 0].sum()
            out[s] = {"trades": int(g.loc[s, "count"]), "pnl": round(float(g.loc[s, "sum"]), 1), "pf": round(float(w / l), 3) if l > 0 else None}
    return out


def report(batches: list[int]) -> str:
    cands, bat, cal = load(batches)
    n = len(cands)
    L = []
    L.append(f"# Exploration campaign report — batches {batches[0]}–{batches[-1]}\n")
    started = min((b["started"] for b in bat), default="—")
    finished = max((b["finished"] or "" for b in bat), default="—")
    trials = max((b["trials_total"] or 0 for b in bat), default=0)
    L.append(f"**{n} strategies tested** in {len(bat)} batches ({started} → {finished}). "
             f"Deflated-Sharpe trial count at the end: {trials} (8,000 legacy configurations + every pipeline trial). "
             f"DSR is recorded but **not blocking** (decision 2026-10-04). Nothing here is promoted to live trading.\n")
    L.append("Data: development = 133 engine coins with data (2021-01 → 2026-09, 1h, real funding, fee 0.05% + slippage 0.05% per side). "
             "Out-of-sample = 280 crypto coins never used by any research (20 delisted). Profit factor and P&L in nominal units "
             "(each trade 100 USDT notional, 1,000 per coin).\n")

    # ---- funnel
    stage = Counter(c["stage"] for c in cands)
    status = Counter(c["status"] for c in cands)
    L.append("## 1. Funnel — where strategies stop\n")
    reached = n
    rows = []
    for s in STAGE_ORDER:
        out_here = stage.get(s, 0) if s not in ("G4", "G5") else None
        if s == "G4":
            out_here = sum(1 for c in cands if c["stage"] == "G4")
        if s == "G5":
            out_here = sum(1 for c in cands if c["stage"] == "G5" and c["status"] != "VALIDATED")
        rows.append([s, reached, out_here, reached - (out_here or 0)])
        reached -= out_here or 0
    L.append(table(["Stage", "Entered", "Stopped here", "Passed"], rows))
    L.append(f"\nFinal status: " + ", ".join(f"**{k}** {v}" for k, v in status.most_common()) + "\n")

    # ---- failure distribution per gate
    L.append("## 2. Failure distribution per gate\n")
    L.append("A strategy can fail several gates; counts are over strategies on which the gate was evaluated.\n")
    gstat = defaultdict(Counter)
    for c in cands:
        for name, (res, _) in c["g"].items():
            gstat[name][res] += 1
    order = sorted(gstat, key=lambda x: (x[:2], x))
    L.append(table(["Gate", "Evaluated", "Pass", "Fail", "Fail rate", "No data"],
                   [[g, gstat[g]["pass"] + gstat[g]["fail"], gstat[g]["pass"], gstat[g]["fail"],
                     f"{gstat[g]['fail'] / max(1, gstat[g]['pass'] + gstat[g]['fail']):.0%}", gstat[g]["n/a"]] for g in order]))

    # ---- best candidates
    L.append("\n## 3. Best candidates\n")
    ranked = sorted([c for c in cands if (c["dev"].get("trades") or 0) >= 300],
                    key=lambda c: (STAGE_ORDER.index(c["stage"]) if c["stage"] in STAGE_ORDER else -1, c["dev"].get("pf") or 0), reverse=True)[:20]
    L.append("Top 20 by furthest gate reached, then development profit factor (≥ 300 trades).\n")
    L.append(table(["#", "Strategy", "Status / stopped at", "Dev PF", "PF 2x costs", "t-stat", "Random pctl", "DSR",
                    "Coins +", "Regimes +", "Port. DD %", "OOS PF", "OOS trades"],
                   [[i + 1, c["name"], f"{c['status']} / {c['stage']}", f(c["dev"].get("pf"), 3), f(c["dev2"].get("pf"), 3),
                     f(c["dev"].get("t_stat")), f(c["dev"].get("random_pct"), 1), f(c["dev"].get("dsr"), 3),
                     f"{c['dev'].get('coins_profitable')}/{c['dev'].get('coins')}",
                     f"{sum(1 for v in (c['dev'].get('regimes') or {}).values() if v > 0)}/4",
                     f((c["dev"].get("portfolio_10") or {}).get("max_dd"), 1), f(c["oos"].get("pf"), 3), c["oos"].get("trades", "—")]
                    for i, c in enumerate(ranked)]))
    for c in ranked[:5]:
        L.append(f"\n**{c['name']}** — {c['status']} at {c['stage']}. {c['reason']}  \n"
                 f"Entry: {c['entry_desc']}  \nExit: {c['exit_desc']}  \nRegimes (dev): {c['dev'].get('regimes')}")

    # ---- families
    L.append("\n## 4. Strategy-family performance\n")
    fam = defaultdict(list)
    for c in cands:
        fam[c["family"]].append(c)
    rows = []
    for k, cs in sorted(fam.items(), key=lambda kv: -(med([c["dev"].get("pf") for c in kv[1]]) or 0)):
        pfs = [c["dev"].get("pf") for c in cs]
        rows.append([k + (" (new)" if k in NEW_FAMILIES else ""), len(cs), f(med(pfs), 3), f(max([p for p in pfs if p is not None], default=None), 3),
                     sum(1 for p in pfs if p and p > 1), sum(1 for c in cs if (c["dev"].get("random_pct") or 0) >= 95),
                     sum(1 for c in cs if c["stage"] not in ("G1", "G2")), sum(1 for c in cs if c["status"] in ("PROMISING", "VALIDATED"))])
    L.append(table(["Family", "Tested", "Median dev PF", "Best dev PF", "PF > 1", "Beat random p95", "Passed G2", "Promising+"], rows))

    # ---- long / short
    L.append("\n## 5. Long / short breakdown\n")
    rows = []
    for d in ("long", "short", "both"):
        cs = [c for c in cands if c["spec"].get("direction") == d]
        if cs:
            rows.append([d, len(cs), f(med([c["dev"].get("pf") for c in cs]), 3), sum(1 for c in cs if (c["dev"].get("pf") or 0) > 1),
                         sum(1 for c in cs if c["stage"] not in ("G1", "G2")), sum(1 for c in cs if c["status"] in ("PROMISING", "VALIDATED"))])
    L.append(table(["Direction", "Tested", "Median dev PF", "PF > 1", "Passed G2", "Promising+"], rows))
    both = [(c, side_split(c["id"])) for c in cands if c["spec"].get("direction") == "both"]
    both = [(c, s) for c, s in both if s]
    if both:
        lp = [s["long"]["pnl"] for c, s in both if "long" in s]
        sp = [s["short"]["pnl"] for c, s in both if "short" in s]
        L.append(f"\nInside the {len(both)} two-sided strategies (from saved trades): long legs total {sum(lp):+,.0f}, "
                 f"short legs total {sum(sp):+,.0f}; short leg profitable in {sum(1 for x in sp if x > 0)}/{len(sp)}.")

    # ---- costs
    L.append("\n## 6. Costs\n")
    pairs = [(c["dev"].get("pf"), c["dev2"].get("pf"), c) for c in cands if c["dev"].get("pf") and c["dev2"].get("pf")]
    flip = [c for a, b, c in pairs if a > 1 >= b]
    drop = [a - b for a, b, _ in pairs]
    L.append(f"Doubling fees and slippage (0.10% + 0.10% per side) lowered profit factor by a median {f(med(drop), 3)} "
             f"(range {f(min(drop, default=None), 3)} to {f(max(drop, default=None), 3)}). "
             f"{sum(1 for a, b, _ in pairs if a > 1)} strategies were profitable at base costs; {len(flip)} of them turned unprofitable at 2x costs.")
    hi_turn = sorted(cands, key=lambda c: -(c["dev"].get("trades") or 0))[:5]
    L.append("\nMost active strategies (cost-sensitive): " + "; ".join(f"{c['name']} — {c['dev'].get('trades')} trades, PF {f(c['dev'].get('pf'), 3)} → {f(c['dev2'].get('pf'), 3)}" for c in hi_turn))

    # ---- holdout
    L.append("\n## 7. Out-of-sample (280 unseen coins) and time folds\n")
    oos = [c for c in cands if c["oos"]]
    if not oos:
        L.append("No strategy reached the out-of-sample stage.")
    else:
        L.append(table(["Strategy", "Dev PF", "OOS PF", "OOS trades", "OOS coins +", "Expectancy kept", "OOS random pctl", "Time folds +", "Status"],
                       [[c["name"], f(c["dev"].get("pf"), 3), f(c["oos"].get("pf"), 3), c["oos"].get("trades"),
                         f"{c['oos'].get('coins_profitable')}/{c['oos'].get('coins')}", c["g"].get("G4 expectancy kept", ("", "—"))[1],
                         f(c["oos"].get("random_pct"), 1), c["g"].get("G5 time-fold consistency", ("", "—"))[1], c["status"]] for c in oos]))

    # ---- drawdowns
    L.append("\n## 8. Drawdowns (10-slot compounding portfolio, development coins)\n")
    prof = [c for c in cands if (c["dev"].get("pf") or 0) > 1]
    dds = [(c["dev"].get("portfolio_10") or {}).get("max_dd") for c in prof]
    dds = [x for x in dds if x is not None]
    L.append(f"Among the {len(prof)} strategies with dev PF > 1: median max drawdown {f(med(dds), 1)}%, "
             f"{sum(1 for x in dds if x <= 40)} within the 40% bar." if dds else "No profitable strategy to report drawdowns for.")
    if prof:
        L.append("\n" + table(["Strategy", "Dev PF", "Portfolio return %", "Max DD %", "Trades taken / skipped"],
                              [[c["name"], f(c["dev"].get("pf"), 3), f((c["dev"].get("portfolio_10") or {}).get("ret_pct"), 1),
                                f((c["dev"].get("portfolio_10") or {}).get("max_dd"), 1),
                                f"{(c['dev'].get('portfolio_10') or {}).get('taken')}/{(c['dev'].get('portfolio_10') or {}).get('skipped')}"]
                               for c in sorted(prof, key=lambda c: -(c['dev'].get('pf') or 0))[:15]]))

    # ---- DSR
    L.append("\n## 9. Deflated Sharpe ratio (recorded, not blocking)\n")
    ds = [c["dev"].get("dsr") for c in cands if c["dev"].get("dsr") is not None]
    L.append(f"Recorded for {len(ds)} strategies: ≥ 0.95 in {sum(1 for x in ds if x >= 0.95)}, 0.5–0.95 in {sum(1 for x in ds if 0.5 <= x < 0.95)}, "
             f"< 0.5 in {sum(1 for x in ds if x < 0.5)}. Highest: {f(max(ds, default=None), 3)}.")
    calg = cal["g"]
    if calg:
        cd = cal["m"].get("dev", {})
        L.append(f"\nReference — VBreak4Live's rules through the same gates (calibration): dev PF {f(cd.get('pf'), 3)}, t-stat {f(cd.get('t_stat'))}, "
                 f"random pctl {f(cd.get('random_pct'), 1)}, DSR {f(cd.get('dsr'), 3)}, portfolio DD {f((cd.get('portfolio_10') or {}).get('max_dd'), 1)}%.")

    L.append("\n## 10. Caveats\n")
    L.append("- Every result is a backtest. Promising/validated here means *worth a forward test*, not *approved for live trading*.\n"
             "- Development coins were mined by earlier research too (≈ 8,000 configurations); only the out-of-sample stage is clean.\n"
             "- Each strategy is one random draw of parameters from its family; a family that fails here may still contain a working variant.\n"
             "- Random-entry replicas ignore funding; this makes the baseline slightly easier to beat, not harder.\n"
             "- Portfolio drawdown uses a simple compounding 10-slot model (no correlation cap), comparable across strategies, not a live forecast.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batches", default="4-13")
    ap.add_argument("--out")
    a = ap.parse_args()
    lo, _, hi = a.batches.partition("-")
    bs = list(range(int(lo), int(hi or lo) + 1))
    md = report(bs)
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
