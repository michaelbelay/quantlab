"""Walk-forward for the harvested families, with selection inside each fold.

Scoring `trend_resume | btc | long` on its own full history would launder the
fact that it was CHOSEN from a 30-combination screen. So each fold re-runs the
choice: rank every combination on the train window, take the winner, and report
what it then did on the window that follows -- which selection never saw.

Following run.py's argument, one full-span simulation per combination is
sufficient: no strategy parameter is fitted to the data, only the selection is,
so slicing the resulting trades by entry date introduces no leakage and costs
no extra backtest time.

Two things are reported:
  1. the walk-forward result (selection re-run per fold), and
  2. the per-period and per-regime record of the single leading candidate,
     which is what tells us whether 2025-26 is survivable or fatal.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "engine"))
from backtest import Config, simulate                    # noqa: E402
from features import DEV_COINS, load_universe            # noqa: E402
from tournament import metrics                           # noqa: E402

OUT = HERE / "engine_results" / "harvest_walkforward.json"
CACHE = HERE / "harvest_trades_cache.parquet"

FAMILIES = ["trend_resume", "rsi_reset", "band_fade_confirmed"]
FILTERSETS = {"nofilt": [], "vol": ["volume"], "btc": ["btc_regime"],
              "btc+vol": ["btc_regime", "volume"], "notflat": ["not_flat"]}
DIRECTIONS = ["both", "long"]

FOLDS = [  # (train_start, train_end / oos_start, oos_end)
    ("2021-01-01", "2022-07-01", "2023-01-01"),
    ("2021-07-01", "2023-01-01", "2023-07-01"),
    ("2022-01-01", "2023-07-01", "2024-01-01"),
    ("2022-07-01", "2024-01-01", "2024-07-01"),
    ("2023-01-01", "2024-07-01", "2025-01-01"),
    ("2023-07-01", "2025-01-01", "2025-07-01"),
    ("2024-01-01", "2025-07-01", "2026-01-01"),
    ("2024-07-01", "2026-01-01", "2026-10-01"),
]
REGIMES = [("bull2021", "2021-01-01", "2021-11-10"),
           ("bear2022", "2021-11-10", "2023-01-01"),
           ("recovery2023_24", "2023-01-01", "2025-01-01"),
           ("recent2025_26", "2025-01-01", "2026-10-01")]
MIN_TRADES_TRAIN = 30
WALLET = 1000.0


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def build_cache(uni):
    """One simulation per combination; trades tagged with entry/exit dates."""
    rows = []
    cfg = Config(leverage=1.0, stop_mode="atr", stop_atr=2.0, tp_mode="none",
                 tp_atr=(), tp_frac=(), entry_mode="instant")
    for fam in FAMILIES:
        for fname, filts in FILTERSETS.items():
            for direction in DIRECTIONS:
                spec = {"family": fam, "direction": direction, "filters": filts,
                        "trend_mode": "with", "params": {}}
                tr = simulate(uni, spec, cfg)
                cid = f"{fam}|{fname}|{direction}"
                for t in tr:
                    dates = uni[t.pair].date
                    rows.append({"cid": cid, "pair": t.pair, "pnl": t.pnl,
                                 "r": t.r,
                                 "entry_date": pd.Timestamp(dates[t.entry_i]),
                                 "exit_date": pd.Timestamp(dates[min(t.exit_i, len(dates) - 1)])})
                print(f"  simulated {cid:44} {len(tr):>6} trades", flush=True)
    df = pd.DataFrame(rows)
    df.to_parquet(CACHE)
    return df


def window(df, a, b):
    m = (df.entry_date >= ts(a)) & (df.entry_date < ts(b))
    return df[m]


def ret_pct(sub):
    return sub.pnl.sum() / WALLET * 100.0


def main():
    uni = load_universe(DEV_COINS, futures=True)
    if CACHE.exists():
        df = pd.read_parquet(CACHE)
        print(f"loaded cached trades: {len(df):,}", flush=True)
    else:
        print("simulating all combinations once over the full span...", flush=True)
        df = build_cache(uni)
    if df.entry_date.dt.tz is None:
        df["entry_date"] = df.entry_date.dt.tz_localize("UTC")

    out = {"folds": [], "leader": {}}
    print("\n=== WALK-FORWARD (selection re-run inside each fold) ===", flush=True)
    total = 0.0
    for tr_s, split, oos_e in FOLDS:
        train = window(df, tr_s, split)
        best, best_ret = None, -1e9
        for cid, g in train.groupby("cid"):
            if len(g) < MIN_TRADES_TRAIN:
                continue
            r = ret_pct(g)
            if r > best_ret:
                best, best_ret = cid, r
        oos = window(df[df.cid == best], split, oos_e) if best else None
        o_ret = ret_pct(oos) if oos is not None and len(oos) else 0.0
        total += o_ret
        rec = {"train": f"{tr_s}->{split}", "oos": f"{split}->{oos_e}",
               "picked": best, "train_ret": round(best_ret, 2),
               "oos_ret": round(o_ret, 2),
               "oos_trades": int(len(oos)) if oos is not None else 0}
        out["folds"].append(rec)
        print(f"  train {rec['train']:23} -> oos {rec['oos']:23} "
              f"pick={str(best):40} train {rec['train_ret']:>8}%  OOS {rec['oos_ret']:>8}% "
              f"({rec['oos_trades']} tr)", flush=True)
    pos = sum(1 for f in out["folds"] if f["oos_ret"] > 0)
    out["oos_sum"] = round(total, 2)
    out["folds_positive"] = f"{pos}/{len(FOLDS)}"
    print(f"\n  OOS sum {total:+.2f}%   folds positive {pos}/{len(FOLDS)}", flush=True)

    lead = "trend_resume|btc|long"
    ld = df[df.cid == lead]
    print(f"\n=== LEADER {lead}: per half-year ===", flush=True)
    hy = {}
    for y in range(2021, 2027):
        for half, (a, b) in enumerate([(f"{y}-01-01", f"{y}-07-01"),
                                       (f"{y}-07-01", f"{y+1}-01-01")]):
            if ts(a) > ts("2026-10-01"):
                continue
            sub = window(ld, a, b)
            if len(sub) == 0:
                continue
            key = f"{y}H{half+1}"
            hy[key] = {"ret": round(ret_pct(sub), 2), "trades": int(len(sub))}
            print(f"  {key:8} {hy[key]['ret']:>9}%  ({hy[key]['trades']} trades)", flush=True)
    out["leader"]["half_years"] = hy
    print(f"\n=== LEADER: per regime ===", flush=True)
    rg = {}
    for name, a, b in REGIMES:
        sub = window(ld, a, b)
        rg[name] = {"ret": round(ret_pct(sub), 2), "trades": int(len(sub))}
        print(f"  {name:18} {rg[name]['ret']:>9}%  ({rg[name]['trades']} trades)", flush=True)
    out["leader"]["regimes"] = rg
    out["leader"]["cid"] = lead

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT}", flush=True)
    print("WALKFORWARD_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
