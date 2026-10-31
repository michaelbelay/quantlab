"""Switcher (2026-10-24): weekly, hold the reversal book or the momentum basket, whichever earned more over the last
8 weeks. Rule: REGISTER_SWITCHER_2026-10-24.md.

    cd research\\fresh && ..\\..\\.venv\\Scripts\\python.exe switcher.py
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import bear_batch as bb

S, E = pd.Timestamp("2022-02-07", tz="UTC"), pd.Timestamp("2026-10-01", tz="UTC")
bb.START, bb.END = S, E
btc = pd.read_feather(bb.DATA / "BTC_USDT_USDT-1h-futures.feather").set_index("date").sort_index()
bb.BTC_BEAR = (btc["close"] < btc["close"].rolling(1200).mean()).shift(1)
bb.BTC_RET168 = btc["close"] / btc["close"].shift(168) - 1

rev, closes = [], {}
for p in bb.PAIRS:
    f = bb.DATA / f"{p.split('/')[0]}_USDT_USDT-1h-futures.feather"
    if not f.exists():
        continue
    df = pd.read_feather(f).set_index("date").sort_index()
    if len(df) < 500:
        continue
    closes[p] = df["close"]
    sigs, _ = bb.signals(df)
    for k in ("rally_short", "flush_long"):
        side, sl, tp, hold = bb.IDEAS[k]
        rev += [(a, b, net) for a, b, net in bb.simulate(df, sigs[k].fillna(False).astype(bool), side, sl, tp, hold)]

R = pd.DataFrame(rev, columns=["open", "close", "net"])
wk = lambda s: (s - pd.to_timedelta(s.dt.dayofweek, unit="D")).dt.normalize()  # noqa: E731
r_week = R.groupby(wk(R["open"]))["net"].mean()          # what holding R that week earned (trades opened that week)
r_known = R.groupby(wk(R["close"]))["net"].mean()        # what was KNOWN by the end of that week (trades closed then)

C = pd.DataFrame(closes)
rows = []
for t0 in C.index[(C.index.dayofweek == 0) & (C.index.hour == 0) & (C.index >= S) & (C.index < E)]:
    t1, tm = t0 + pd.Timedelta(hours=168), t0 - pd.Timedelta(days=30)
    if t1 not in C.index or tm not in C.index:
        continue
    mom = (C.loc[t0] / C.loc[tm] - 1).dropna()
    fwd = C.loc[t1] / C.loc[t0] - 1
    mom = mom[fwd.reindex(mom.index).notna()]
    if len(mom) < 40:
        continue
    lo, sh = fwd[mom.nlargest(10).index].mean() - bb.COST, -fwd[mom.nsmallest(10).index].mean() - bb.COST
    rows.append((t0.normalize(), (lo + sh) / 2))
m_week = pd.Series(dict(rows))

W = pd.DataFrame({"R": r_week, "M": m_week, "R_known": r_known}).sort_index()
W = W[W["M"].notna()].fillna({"R": 0.0, "R_known": 0.0})
# choice uses only closed results: R by close week, M week t0 is known at t0+7d (its own Monday close)
trail = W[["R_known", "M"]].rename(columns={"R_known": "R"}).rolling(8).mean().shift(1)
pick = np.where(trail.max(axis=1) <= 0, "cash", np.where(trail["R"] >= trail["M"], "R", "M"))
pick[trail.isna().any(axis=1).to_numpy()] = "cash"
W["pick"] = pick
W["sw"] = [W.loc[i, p] if p != "cash" else 0.0 for i, p in zip(W.index, W["pick"])]
W["year"] = W.index.year
yr = W.groupby("year")[["R", "M", "sw"]].mean().mul(100).round(2)
tot = W[["R", "M", "sw"]].sum().mul(100).round(1)
ok = (yr["sw"] > 0).sum() >= 4 and tot["sw"] > tot["R"] and tot["sw"] > tot["M"]
out = {"weeks": int(len(W)), "per_year_avg_week_pct": yr.to_dict(orient="index"), "sum_of_weeks_pct": tot.to_dict(),
       "weeks_pos_switcher_pct": round(float((W.loc[W.pick != "cash", "sw"] > 0).mean() * 100), 1),
       "picked": W["pick"].value_counts().to_dict(), "verdict": "🟡 paper forward test" if ok else "🔴"}
W.to_csv(bb.HERE / "bear_batch" / "switcher_weeks.csv")
print(json.dumps(out, indent=1, default=str))
txt = (f"\n## Re-run without look-ahead (2026-10-24, rule unchanged; the first run let Monday's choice see reversal trades "
       f"that closed later in the week; now the choice uses closed trades only, the week's profit uses trades opened that week)\nper year, average weekly %: {yr.to_dict(orient='index')}\n"
       f"sum of weekly %: {tot.to_dict()} | picked {out['picked']} | verdict {out['verdict']}\n")
(bb.HERE / "REGISTER_SWITCHER_2026-10-24.md").open("a", encoding="utf-8").write(txt)
print("DONE")
