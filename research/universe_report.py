"""Breakdowns for the 140-coin run: coin, cap group, volatility, regime, side, family.

Reads only what universe_run.py already wrote, so the report can never disagree
with the run. Answers one question: do the existing strategies generalize beyond
the 16 coins they were discovered on?
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "engine"))
from features import load_pair  # noqa: E402

UNI = ROOT / "data" / "market" / "universe"
WALLET = 1000.0
ORIGINAL_16 = {"BTC", "ETH", "SOL", "XRP", "LINK", "LTC", "ADA", "AVAX",
               "DOGE", "DOT", "ATOM", "UNI", "BCH", "ETC", "TRX", "NEAR"}
REGIMES = [("bull2021", "2021-01-01", "2021-11-10"),
           ("bear2022", "2021-11-10", "2023-01-01"),
           ("recovery2023_24", "2023-01-01", "2025-01-01"),
           ("recent2025_26", "2025-01-01", "2026-10-01")]


def cap_group(rank):
    if rank is None:
        return "unranked"
    if rank <= 10:
        return "mega (1-10)"
    if rank <= 50:
        return "large (11-50)"
    if rank <= 150:
        return "mid (51-150)"
    return "small (151+)"


def main():
    led = [json.loads(l) for l in (HERE / "universe_ledger.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    led = [r for r in led if r.get("status") == "ok"]
    if not led:
        print("no completed combinations yet"); return
    L = pd.DataFrame(led)
    uni = {c["base"]: c for c in json.loads((UNI / "universe_150.json").read_text(encoding="utf-8"))["coins"]}

    print("=" * 96)
    print("COMBINATIONS (dev set)")
    print("=" * 96)
    d = L[L.set == "dev"].sort_values("ret_pct", ascending=False)
    print(f"{'combination':40}{'trades':>8}{'ret%':>9}{'PF':>7}{'coins+':>9}{'long':>9}{'short':>9}")
    for _, r in d.iterrows():
        print(f"{r.cid:40}{r.trades:>8}{r.ret_pct:>9}{r.pf or 0:>7}"
              f"{r.coins_profitable}/{r.coins_traded:<6}{r.long_pnl:>9}{r.short_pnl:>9}")

    print("\n" + "=" * 96)
    print("BY REGIME (dev set)")
    print("=" * 96)
    print(f"{'combination':40}" + "".join(f"{n:>17}" for n, _, _ in REGIMES))
    for _, r in d.iterrows():
        print(f"{r.cid:40}" + "".join(f"{r[n]:>17}" for n, _, _ in REGIMES))
    n_recent = int((d.recent2025_26 > 0).sum())
    print(f"\n  profitable in recent2025_26: {n_recent}/{len(d)}")

    print("\n" + "=" * 96)
    print("LONG vs SHORT (dev set, 'both' variants only)")
    print("=" * 96)
    b = d[d.direction == "both"]
    print(f"{'combination':40}{'long pnl':>11}{'long tr':>9}{'short pnl':>11}{'short tr':>10}{'short share':>13}")
    for _, r in b.iterrows():
        tot = abs(r.long_pnl) + abs(r.short_pnl)
        share = f"{abs(r.short_pnl)/tot*100:.0f}%" if tot else "—"
        print(f"{r.cid:40}{r.long_pnl:>11}{r.long_trades:>9}{r.short_pnl:>11}{r.short_trades:>10}{share:>13}")

    # ---- per-coin, from the trade files of the best combination ----
    best = d.iloc[0]
    f = HERE / "universe_trades" / f"{best.cid.replace('|','~')}__dev.parquet"
    if f.exists():
        t = pd.read_parquet(f)
        per = t.groupby("pair").agg(pnl=("pnl", "sum"), trades=("pnl", "size"))
        per["cap_rank"] = [uni.get(p, {}).get("market_cap_rank") for p in per.index]
        per["group"] = per.cap_rank.map(cap_group)
        per["in_original_16"] = [p in ORIGINAL_16 for p in per.index]

        print("\n" + "=" * 96)
        print(f"GENERALISATION TEST — {best.cid}")
        print("=" * 96)
        o = per[per.in_original_16]
        n = per[~per.in_original_16]
        for lab, g in (("original 16 coins", o), ("the other coins", n)):
            if len(g):
                print(f"  {lab:20} {len(g):>3} coins  pnl {g.pnl.sum():>9.1f}  "
                      f"profitable {int((g.pnl>0).sum())}/{len(g)}  "
                      f"mean/coin {g.pnl.mean():>7.2f}")
        print("\n  BY MARKET-CAP GROUP")
        grp = per.groupby("group").agg(coins=("pnl", "size"), pnl=("pnl", "sum"),
                                       profitable=("pnl", lambda s: int((s > 0).sum())),
                                       trades=("trades", "sum"))
        print(grp.round(1).to_string())

        # volatility bucket from each coin's own ATR%
        vols = {}
        for p in per.index:
            fp = load_pair(p, futures=True)
            if fp is not None:
                vols[p] = float(np.nanmedian(fp.atr_pct.to_numpy()))
        per["atr_pct"] = [vols.get(p) for p in per.index]
        per["vol_bucket"] = pd.qcut(per.atr_pct, 3, labels=["low vol", "mid vol", "high vol"])
        print("\n  BY VOLATILITY (median ATR% per coin)")
        vb = per.groupby("vol_bucket", observed=True).agg(
            coins=("pnl", "size"), pnl=("pnl", "sum"),
            profitable=("pnl", lambda s: int((s > 0).sum())))
        print(vb.round(1).to_string())

        print("\n  WORST 8 COINS");  print(per.nsmallest(8, "pnl")[["pnl", "trades", "group"]].round(1).to_string())
        print("\n  BEST 8 COINS");   print(per.nlargest(8, "pnl")[["pnl", "trades", "group"]].round(1).to_string())
        per.to_parquet(HERE / "universe_per_coin.parquet")

    # ---- dev vs holdout ----
    h = L[L.set == "holdout"]
    if len(h):
        print("\n" + "=" * 96)
        print("DEV vs HOLDOUT (rule-based split, alternating market-cap rank)")
        print("=" * 96)
        m = d.merge(h, on="cid", suffixes=("_dev", "_hold"))
        print(f"{'combination':40}{'dev ret%':>11}{'hold ret%':>12}{'dev PF':>9}{'hold PF':>9}")
        for _, r in m.iterrows():
            print(f"{r.cid:40}{r.ret_pct_dev:>11}{r.ret_pct_hold:>12}"
                  f"{r.pf_dev or 0:>9}{r.pf_hold or 0:>9}")
    print("\nUNIVERSE_REPORT_COMPLETE")


if __name__ == "__main__":
    main()
