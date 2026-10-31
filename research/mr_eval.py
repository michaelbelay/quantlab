"""Mean-reversion expansion: one pass, every stage.

Why this exists: regime attribution on the first harvest showed every trend
family losing 27-106 points in recent2025_26 while the counter-trend family sat
within noise of flat. So the search widens toward mean reversion, and the same
discipline applies -- nothing here is believed until walk-forward.

One simulation per combination over the full span; full-span metrics, the
regime split and the walk-forward are all derived from those cached trades, as
evaluate.py does it. Selection is re-run inside each fold so a leader chosen
from this grid cannot be scored on the history that chose it.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "engine"))
from backtest import Config, simulate                    # noqa: E402
from features import DEV_COINS, load_universe            # noqa: E402
from tournament import SPAN_YEARS, metrics               # noqa: E402

CACHE = HERE / "mr_trades_cache.parquet"
OUT = HERE / "engine_results" / "mr_results.json"

FAMILIES = ["failed_breakout", "vwap_reversion", "streak_exhaustion", "stretch_fade"]
FILTERSETS = {"nofilt": [], "vol": ["volume"], "btc": ["btc_regime"],
              "btc+vol": ["btc_regime", "volume"], "notflat": ["not_flat"]}
DIRECTIONS = ["both", "long"]

REGIMES = [("bull2021", "2021-01-01", "2021-11-10"),
           ("bear2022", "2021-11-10", "2023-01-01"),
           ("recovery2023_24", "2023-01-01", "2025-01-01"),
           ("recent2025_26", "2025-01-01", "2026-10-01")]
FOLDS = [("2021-01-01", "2022-07-01", "2023-01-01"),
         ("2021-07-01", "2023-01-01", "2023-07-01"),
         ("2022-01-01", "2023-07-01", "2024-01-01"),
         ("2022-07-01", "2024-01-01", "2024-07-01"),
         ("2023-01-01", "2024-07-01", "2025-01-01"),
         ("2023-07-01", "2025-01-01", "2025-07-01"),
         ("2024-01-01", "2025-07-01", "2026-01-01"),
         ("2024-07-01", "2026-01-01", "2026-10-01")]
WALLET = 1000.0
MIN_TRAIN = 30


def ts(x):
    return pd.Timestamp(x, tz="UTC")


def win(d, a, b):
    return d[(d.entry_date >= ts(a)) & (d.entry_date < ts(b))]


def ret(sub):
    return sub.pnl.sum() / WALLET * 100.0


def build(uni):
    rows = []
    cfg = Config(leverage=1.0, stop_mode="atr", stop_atr=2.0, tp_mode="none",
                 tp_atr=(), tp_frac=(), entry_mode="instant")
    for fam in FAMILIES:
        for fname, filts in FILTERSETS.items():
            for direction in DIRECTIONS:
                spec = {"family": fam, "direction": direction, "filters": filts,
                        "trend_mode": "with", "params": {}}
                t0 = time.time()
                tr = simulate(uni, spec, cfg)
                cid = f"{fam}|{fname}|{direction}"
                for t in tr:
                    dates = uni[t.pair].date
                    rows.append({"cid": cid, "pair": t.pair, "pnl": t.pnl,
                                 "entry_date": pd.Timestamp(dates[t.entry_i])})
                print(f"  {cid:46}{len(tr):>7} trades  ({round(time.time()-t0)}s)", flush=True)
    df = pd.DataFrame(rows)
    df.to_parquet(CACHE)
    return df


def main():
    uni = load_universe(DEV_COINS, futures=True)
    if CACHE.exists():
        df = pd.read_parquet(CACHE)
        print(f"cached trades: {len(df):,}", flush=True)
    else:
        print("simulating...", flush=True)
        df = build(uni)
    if df.entry_date.dt.tz is None:
        df["entry_date"] = df.entry_date.dt.tz_localize("UTC")

    res = {"combos": [], "walkforward": {}}
    print(f"\n{'combination':46}{'full%':>9}{'trades':>8}{'bull21':>9}"
          f"{'bear22':>9}{'rec23_24':>10}{'RECENT':>9}", flush=True)
    for cid, g in df.groupby("cid"):
        row = {"cid": cid, "full_ret": round(ret(g), 1), "trades": int(len(g))}
        for n, a, b in REGIMES:
            sub = win(g, a, b)
            row[n] = round(ret(sub), 1)
            row[n + "_tr"] = int(len(sub))
        res["combos"].append(row)
    res["combos"].sort(key=lambda r: -r["recent2025_26"])
    for r in res["combos"]:
        print(f"{r['cid']:46}{r['full_ret']:>9}{r['trades']:>8}{r['bull2021']:>9}"
              f"{r['bear2022']:>9}{r['recovery2023_24']:>10}{r['recent2025_26']:>9}", flush=True)

    print("\n=== WALK-FORWARD (selection re-run inside each fold) ===", flush=True)
    folds, total = [], 0.0
    for a, split, b in FOLDS:
        train = win(df, a, split)
        best, best_r = None, -1e9
        for cid, g in train.groupby("cid"):
            if len(g) < MIN_TRAIN:
                continue
            r = ret(g)
            if r > best_r:
                best, best_r = cid, r
        oos = win(df[df.cid == best], split, b) if best else None
        o = ret(oos) if oos is not None and len(oos) else 0.0
        total += o
        folds.append({"oos": f"{split}->{b}", "picked": best,
                      "train_ret": round(best_r, 2), "oos_ret": round(o, 2),
                      "oos_trades": int(len(oos)) if oos is not None else 0})
        print(f"  oos {split[:7]}->{b[:7]}  pick={str(best):44} "
              f"train {round(best_r,1):>7}%  OOS {round(o,1):>7}% ({folds[-1]['oos_trades']} tr)",
              flush=True)
    pos = sum(1 for f in folds if f["oos_ret"] > 0)
    res["walkforward"] = {"folds": folds, "oos_sum": round(total, 2),
                          "folds_positive": f"{pos}/{len(FOLDS)}"}
    print(f"\n  OOS sum {total:+.2f}%   folds positive {pos}/{len(FOLDS)}", flush=True)
    n_recent = sum(1 for r in res["combos"] if r["recent2025_26"] > 0)
    res["profitable_recent"] = f"{n_recent}/{len(res['combos'])}"
    print(f"  profitable in recent2025_26: {n_recent}/{len(res['combos'])}", flush=True)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("MR_EVAL_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
