r"""Protocol C trade generation: every family of a batch, one timeframe, one coin at a time (resumable).

    .venv\Scripts\python.exe -m quant.gen_c 1h  [--batch BATCH1] [--budget 540]
    .venv\Scripts\python.exe -m quant.gen_c 15m
    .venv\Scripts\python.exe -m quant.gen_c 30m

Writes runs/c_trades/<batch>/<tf>/<coin>.parquet (all periods; evaluation decides what may be looked at)
and <coin>.twins.npz (100 random-timing twin sums of DEV trades per family). Exit code 3 = not finished.
"""
from __future__ import annotations

import argparse
import sys
import time

import numpy as np
import pandas as pd

from strategies import families_c as FC

from . import trades as T
from .bars import bars, universe_15m, universe_1h
from .liquidity import rank_series
from .paths import DATA
from .paths import RUNS

BPD = {"1h": 24, "30m": 48, "15m": 96}
DEV_END = {"1h": "2024-07-01", "30m": "2025-09-01", "15m": "2025-09-01"}
REPS = 2000              # was 100 until 2026-10-09: too noisy near the p95 gate (SE ~2 points)


def twin_sums(df: pd.DataFrame, tr: list[dict], rng: np.random.Generator) -> np.ndarray:
    if not tr:
        return np.zeros(REPS)
    o, c = df["open"].to_numpy(), df["close"].to_numpy()
    side = np.array([t["side"] for t in tr])
    b = np.array([t["bars"] for t in tr])
    lo, hi = tr[0]["entry_i"], tr[-1]["exit_i"]
    cost = 2 * (T.FEE + T.SLIP)
    out = np.zeros(REPS)
    span = np.maximum(hi - b + 1 - lo, 1)
    for r in range(REPS):
        e = lo + (rng.random(len(b)) * span).astype(int)
        x = np.minimum(e + b - 1, len(c) - 1)
        with np.errstate(invalid="ignore", divide="ignore"):
            rr = side * (c[x] / o[e] - 1) - cost
        out[r] = np.nansum(rr)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tf", choices=list(BPD))
    ap.add_argument("--batch", default="BATCH1")
    ap.add_argument("--budget", type=float, default=540)
    a = ap.parse_args()
    fams = getattr(FC, a.batch)
    out_dir = RUNS / "c_trades" / a.batch / a.tf
    out_dir.mkdir(parents=True, exist_ok=True)
    coins = universe_1h() if a.tf == "1h" else universe_15m()
    btc_df = bars("BTC", a.tf).set_index("date")
    btc = btc_df["close"]
    dev_end = pd.Timestamp(DEV_END[a.tf], tz="UTC")
    liq = pd.read_parquet(DATA / "liq_rank.parquet") if (DATA / "liq_rank.parquet").exists() else None
    t0, done = time.time(), 0
    for coin in coins:
        f_out = out_dir / f"{coin}.parquet"
        if f_out.exists():
            done += 1
            continue
        df = bars(coin, a.tf)
        if len(df) < 40 * BPD[a.tf]:
            pd.DataFrame().to_parquet(f_out)
            done += 1
            continue
        atr_ = T.atr(df)
        ctx = {"bpd": BPD[a.tf], "tf": a.tf, "btc": btc.reindex(df["date"]).reset_index(drop=True) if coin != "BTC" else None}
        bal = btc_df.reindex(df["date"]) if coin != "BTC" else None          # hedge leg, aligned to this coin
        ctx["liq_rank"] = rank_series(coin, df["date"], liq) if liq is not None else None
        rows, twins = [], {}
        rng = np.random.default_rng(abs(hash((coin, a.tf))) % 2**32)
        for fid, fn in fams.items():
            ls, ss, ex = fn(df, atr_, ctx)
            tr = T.simulate(df, ls, ss, ex, atr_, BPD[a.tf])
            if getattr(fn, "hedge", False):
                if bal is None:
                    tr = []
                else:
                    bo, bc, bf = bal["open"].to_numpy(), bal["close"].to_numpy(), bal["fund"].to_numpy()
                    kept = []
                    for t in tr:
                        e, x = t["entry_i"], t["exit_i"]
                        if not (np.isfinite(bo[e]) and np.isfinite(bc[x])):
                            continue
                        hs = -t["side"]                                   # hedge side
                        h_ret = hs * (bc[x] / bo[e] - 1) - 2 * (T.FEE + T.SLIP) - hs * np.nansum(bf[e:x + 1])
                        t["ret"] = (t["ret"] + h_ret) / 2                 # per unit of total notional (two legs)
                        t["gross"] = (t["gross"] + hs * (bc[x] / bo[e] - 1)) / 2
                        kept.append(t)
                    tr = kept
            for t in tr:
                t["family"], t["coin"] = fid, coin
            rows += tr
            dev_tr = [t for t in tr if pd.Timestamp(t["entry_t"]).tz_localize("UTC") < dev_end] if tr and \
                pd.Timestamp(tr[0]["entry_t"]).tzinfo is None else [t for t in tr if pd.Timestamp(t["entry_t"]) < dev_end]
            twins[fid] = twin_sums(df, dev_tr, rng)
        res = pd.DataFrame(rows)
        if len(res):
            res = res.drop(columns=["entry_i", "exit_i"])
        res.to_parquet(f_out)
        np.savez(out_dir / f"{coin}.twins.npz", **twins)
        done += 1
        if done % 25 == 0:
            print(f"  {a.tf}: {done}/{len(coins)} coins, {time.time() - t0:.0f}s", flush=True)
        if time.time() - t0 > a.budget:
            print(f"budget reached at {done}/{len(coins)}")
            return 3
    print(f"{a.tf}: complete ({len(coins)} coins)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
