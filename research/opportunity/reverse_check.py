"""Idea 7 long check (2026-10-13): BRK_LO20 traded LONG instead of SHORT (same 48h, same target/stop distances),
on the dev coins of split_140 only (no holdout, no unseen coins), 2021 -> data end, per year, vs random long entries
with the same bracket. Changes nothing."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from common import compute_conditions, paths, regular_grid, simulate, triggers
ROOT = Path(__file__).resolve().parents[2]
FUT = ROOT / "data" / "market" / "dev_1h" / "binance" / "futures"
rule = json.loads((Path(__file__).parent / "playbook.json").read_text(encoding="utf-8"))["conditions"]["BRK_LO20"]
H, T, S = rule["hours"], rule["target_sigma"], rule["stop_sigma"]
coins = json.loads((ROOT / "data/market/universe/split_140.json").read_text(encoding="utf-8"))["dev"]
rng = np.random.default_rng(7)
rows = []
for coin in coins:
    f = FUT / f"{coin}_USDT_USDT-1h-futures.feather"
    if not f.exists():
        continue
    fp = FUT / f"{coin}_USDT_USDT-1h-funding_rate.feather"
    x = compute_conditions(regular_grid(pd.read_feather(f)), pd.read_feather(fp) if fp.exists() else None)
    sig = x["sigma24"].to_numpy()
    ok_all = np.flatnonzero(np.isfinite(sig) & (sig > 0) & (x["volume"].to_numpy() > 0))
    for kind, idx in (("signal", triggers(x["BRK_LO20"])), ("random", np.sort(rng.choice(ok_all, min(300, len(ok_all)), replace=False)) if len(ok_all) else ok_all)):
        idx = idx[np.isfinite(sig[idx]) & (sig[idx] > 0)] if len(idx) else idx
        idx, P = paths(x, idx)
        if P is None:
            continue
        net = simulate(P, sig[idx], 1, H, T, S)[0]
        for i, n in zip(idx, net):
            rows.append((kind, coin, x["date"].iloc[i], n * 100))
e = pd.DataFrame(rows, columns=["kind", "coin", "t", "ret"])
e["year"], e["day"] = e.t.dt.year, e.t.dt.strftime("%Y-%m-%d")
def st(g):
    da = g.groupby("day").ret.mean()
    return f"n {len(g):5}  avg {g.ret.mean():+.3f}%  day-avg {da.mean():+.3f}%  t {da.mean()/da.std(ddof=1)*np.sqrt(len(da)):+.2f}  win {(g.ret>0).mean()*100:.0f}%"
print(f"BRK_LO20 as LONG, {H}h, target {T} sigma, stop {S} sigma, {e.coin.nunique()} dev coins")
for y, g in e.groupby("year"):
    print(y, "signal", st(g[g.kind == "signal"]), "| random", st(g[g.kind == "random"]))
print("ALL ", "signal", st(e[e.kind == "signal"]), "| random", st(e[e.kind == "random"]))

b = FUT / "BTC_USDT_USDT-1h-futures.feather"
bx = compute_conditions(regular_grid(pd.read_feather(b)), None).set_index("date")["z24"]
sg = e[e.kind == "signal"].copy()
sg["cluster"] = sg.groupby("t").coin.transform("count")
sg["btcz"] = bx.reindex(sg.t).to_numpy()
for lab, m in (("solo (<3 coins same hour)", sg.cluster < 3), ("<6 coins", sg.cluster < 6),
               ("BTC z24 > -1", sg.btcz > -1), ("solo + BTC z24 > -1", (sg.cluster < 3) & (sg.btcz > -1))):
    g = sg[m]
    print(); print(lab)
    for y, gy in g.groupby("year"):
        print(" ", y, st(gy))
    print("  ALL ", st(g), " sum %+.0f%%" % g.ret.sum())
