"""Waits for the 2x NFI backtest and the CrashShort backtest, then writes research/fresh/MORNING_REPORT_2026-10-23.md
(2x vs 3x, CrashShort, ghost trades). Report only; changes nothing live."""
import json
import sqlite3
import time
import zipfile
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
F = ROOT / "research" / "fresh"
CS = F / "strat_bt" / "CrashShort"
while not ((F / "nfi_lev2_log.txt").exists() and "DONE" in (F / "nfi_lev2_log.txt").read_text(errors="ignore")
           and (CS / "log.txt").exists() and "DONE" in (CS / "log.txt").read_text(errors="ignore")):
    time.sleep(120)
L = ["# Morning report 2026-10-23 (written automatically)", ""]

# ---- 2x vs 3x
a = {r["tag"]: r for r in json.loads((F / "nfi_bt_full223" / "chain_1m.json").read_text())}
b = json.loads((F / "nfi_bt_full223_lev2" / "chain_1m.json").read_text())
rows, s3, s2 = [], 0, 0
for r in b:
    x = a[r["tag"]]
    m3, m2 = (x["end_wallet"] / x["start_wallet"] - 1) * 100, (r["end_wallet"] / 300 - 1) * 100
    s3, s2 = s3 + m3, s2 + m2
    rows.append((r["tag"][:7], m3, m2, min(t["profit_ratio"] for t in x["trades"]) * 100, min(t["profit_ratio"] for t in r["trades"]) * 100))
T3 = [t for x in a.values() for t in x["trades"]]
T2 = [t for r in b for t in r["trades"]]
deep = lambda T: sum(t["profit_ratio"] <= -0.5 for t in T)  # noqa: E731
liq = lambda T: sum("liquidat" in str(t.get("exit_reason", "")).lower() or t["profit_ratio"] <= -0.95 for t in T)  # noqa: E731
ok = deep(T2) < deep(T3) and s2 >= 0.7 * s3
L += ["## NFI at 2x vs 3x (30 months, monthly returns added up)",
      f"- 3x: {s3:+.0f}% | 2x: {s2:+.0f}% -> 2x keeps **{s2 / s3 * 100:.0f}%** of the profit (pass mark 70%)",
      f"- months positive: 3x {sum(r[1] > 0 for r in rows)}/30, 2x {sum(r[2] > 0 for r in rows)}/30",
      f"- trades worse than -50%: 3x {deep(T3)}, 2x {deep(T2)} | liquidation-size losses (<= -95%): 3x {liq(T3)}, 2x {liq(T2)}",
      f"- worst trade: 3x {min(r[3] for r in rows):.1f}%, 2x {min(r[4] for r in rows):.1f}%",
      f"- verdict by the registered rule: **{'2x better' if ok else '2x not better (keeps too little profit)' if deep(T2) < deep(T3) else '2x not better'}**", "",
      "| month | 3x | 2x | worst 3x | worst 2x |", "|---|---|---|---|---|"]
L += [f"| {m} | {x:+.1f}% | {y:+.1f}% | {w3:.1f}% | {w2:.1f}% |" for m, x, y, w3, w2 in rows]
(F / "REGISTER_NFI_LEV2_2026-10-22.md").open("a", encoding="utf-8").write(
    f"\n## Result (automatic, rule unchanged)\n3x {s3:+.0f}% vs 2x {s2:+.0f}% ({s2 / s3 * 100:.0f}%); trades <= -50%: 3x {deep(T3)}, 2x {deep(T2)}; "
    f"verdict: {'2x better' if ok else '2x not better'}\n")

# ---- CrashShort
L += ["", "## CrashShort (short a new 24h low on 2x volume, mirror of BreakoutDay)"]
zips = sorted((CS / "bt").glob("*.zip")) if (CS / "bt").exists() else sorted(CS.glob("bt*.zip"))
if zips:
    with zipfile.ZipFile(zips[-1]) as z:
        n = next(n for n in z.namelist() if n.endswith(".json") and "_config" not in n and "meta" not in n)
        tr = json.loads(z.read(n))["strategy"]["CrashShort"]["trades"]
    d = pd.DataFrame(tr)
    d["m"] = d["open_date"].astype(str).str[:7]
    pm = d.groupby("m")["profit_abs"].sum()
    W, Lo = d[d.profit_abs > 0], d[d.profit_abs <= 0]
    L += [f"- {len(d)} trades, win {len(W) / len(d) * 100:.1f}%, average {d.profit_ratio.mean() * 100:+.2f}% "
          f"(wins {W.profit_ratio.mean() * 100:+.2f}%, losses {Lo.profit_ratio.mean() * 100:+.2f}%), total **{d.profit_abs.sum():+.0f} USDT** at 50/trade",
          f"- months positive: **{(pm > 0).sum()}/{len(pm)}** | exits: {dict(Counter(d.exit_reason))}",
          f"- verdict: **{'🟢/🟡 look closer' if d.profit_abs.sum() > 0 and (pm > 0).sum() >= 20 else '🔴'}**"]
    (F / "REGISTER_CRASH_SHORT_2026-10-22.md").open("a", encoding="utf-8").write(
        f"\n## Result (automatic, rule unchanged)\n{len(d)} trades, win {len(W) / len(d) * 100:.1f}%, avg {d.profit_ratio.mean() * 100:+.2f}%, "
        f"{d.profit_abs.sum():+.0f} USDT, months positive {(pm > 0).sum()}/{len(pm)}\n")
else:
    L += ["- no result file - see research/fresh/strat_bt/CrashShort/log.txt"]

# ---- ghost
L += ["", "## Ghost trades (LUMIA / HUMA / BTW after you closed them, -31.17 USDT)"]
g = F / "ghost" / "as_held.csv"
if g.exists():
    h = pd.read_csv(g)
    last = h.iloc[-1]
    L += [f"- held as they were: {last['held_total_usdt']:+.2f} USDT at {last['time']} -> holding better by {last['holding_better_by']:+.2f}",
          f"- best moment so far: {h.held_total_usdt.max():+.2f}, worst: {h.held_total_usdt.min():+.2f}"]
db = ROOT / "data" / "history" / "paper_ghost_paper.sqlite"
if db.exists():
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    L += [f"- paper NFI managing them: " + "; ".join(f"{p} {'open' if o else 'closed ' + str(round(x or 0, 2))}" for p, o, x in
                                                     c.execute("select pair,is_open,close_profit_abs from trades"))]
(F / "MORNING_REPORT_2026-10-23.md").write_text("\n".join(L) + "\n", encoding="utf-8")
