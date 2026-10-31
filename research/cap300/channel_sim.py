"""300 USDT account simulation of channel long on UP_HIVOL days (602db68df71a), 2026-10-09.

Design fixed before running:
  * start 300 USDT, 1x leverage, at most K = 5 open positions; each new position = realised equity / K
    (skipped when below the coin's Binance minimum notional, or when all slots are taken)
  * signals taken in entry-time order; signals in the same hour are shuffled (20 seeds, report median and range)
  * trade results = engine trades (0.2% round trip incl. slippage, funding, stops); only entries on UP_HIVOL days
  * main data: the 280 unseen coins (2021-01..2026-09-25). Development coins shown for comparison (in-sample).
  * useful for the 300 USDT account if, on unseen coins, the median seed ends above 300, at least 4 of 6 years are
    positive and the max drawdown of realised equity stays under 40% (the live halt rail is 300 -> 180).
  K = 3 and K = 10 are printed for information.
Limitation: equity is realised only (open-trade swings are not marked), so true drawdowns are somewhat larger.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "research"), str(ROOT / "research" / "engine"), str(ROOT / "research" / "incubator"),
                str(ROOT / "research" / "cap300")]
import downtrend as D  # noqa: E402
import incubator as I  # noqa: E402
from regime_switch import market_types  # noqa: E402
from sim import min_notionals  # noqa: E402

CID, A, B = "602db68df71a", "2021-01-01", "2026-09-25"
OUT = ROOT / "research" / "cap300"


def engine_trades(files) -> pd.DataFrame:
    import backtest as BT
    R = I.load_idea(ROOT / "research" / "pipeline" / "run.py")
    con = sqlite3.connect(f"file:{ROOT / 'research' / 'pipeline' / 'pipeline.db'}?mode=ro", uri=True)
    s, c = con.execute("select spec, cfg from candidates where id=?", (CID,)).fetchone()
    spec, cfg = json.loads(s), R.to_cfg(json.loads(c))
    rows = []
    for coin, p, fp in files:
        try:
            f = R.load(p, fp)
        except Exception:
            continue
        if f is None:
            continue
        dates = pd.to_datetime(f.date, utc=True)
        for t in BT.simulate_pair(f, spec, cfg, coin):
            if t.reason == "eod" or not t.notional:
                continue
            rows.append((coin, dates[t.entry_i], dates[t.exit_i], t.pnl / t.notional * 100))
    tr = pd.DataFrame(rows, columns=["coin", "entry", "exit", "pnl"])
    tr = tr[(tr.entry >= pd.Timestamp(A, tz="UTC")) & (tr.entry < pd.Timestamp(B, tz="UTC"))]
    types = market_types()
    return tr[(tr.entry.dt.floor("D").map(types) == "UP_HIVOL").to_numpy()].reset_index(drop=True)


def account(tr: pd.DataFrame, K: int, seed: int, minn: dict) -> dict:
    rng = np.random.default_rng(seed)
    tr = tr.assign(r=rng.random(len(tr))).sort_values(["entry", "r"])
    equity, open_, taken, skipped_slots, skipped_min = 300.0, [], [], 0, 0
    path = []                                              # (time, realised equity)
    for e in tr.itertuples():
        still = []
        for x in sorted(open_, key=lambda x: x[0]):
            if x[0] <= e.entry:
                equity += x[1]
                path.append((x[0], equity))
            else:
                still.append(x)
        open_ = still
        if equity <= 0:
            break
        if len(open_) >= K or any(o[2] == e.coin for o in open_):
            skipped_slots += 1
            continue
        notional = equity / K
        if notional < minn.get(e.coin, 5.0):
            skipped_min += 1
            continue
        pnl = notional * e.pnl / 100
        open_.append((e.exit, pnl, e.coin))
        taken.append((e.entry, e.coin, pnl, e.pnl))
    for x in sorted(open_, key=lambda x: x[0]):
        equity += x[1]
        path.append((x[0], equity))
    p = pd.DataFrame(path, columns=["t", "eq"]).set_index("t")["eq"] if path else pd.Series([300.0])
    t = pd.DataFrame(taken, columns=["entry", "coin", "usdt", "pct"])
    yrs = t.groupby(t.entry.dt.year).usdt.sum() if len(t) else pd.Series(dtype=float)
    return {"final": float(equity), "max_dd": float(-(p / p.cummax().clip(lower=300) - 1).min()) if len(p) else 0.0,
            "taken": int(len(t)), "skipped_full": skipped_slots, "skipped_min": skipped_min,
            "win": float((t.pct > 0).mean() * 100) if len(t) else None,
            "years": {int(y): round(float(v), 1) for y, v in yrs.items()}}


def report(name, tr, minn):
    print(f"\n=== {name}: {len(tr)} signals on UP_HIVOL days, {tr.entry.dt.floor('D').nunique()} days")
    for K in (5, 3, 10):
        runs = [account(tr, K, s, minn) for s in range(20)]
        fin = np.array([r["final"] for r in runs])
        dd = np.array([r["max_dd"] for r in runs])
        med = runs[int(np.argsort(fin)[len(fin) // 2])]
        ypos = sum(v > 0 for v in med["years"].values())
        tag = " <- MAIN" if K == 5 else ""
        print(f" K={K:2d}: final median {np.median(fin):8.1f} (range {fin.min():.1f} .. {fin.max():.1f}) | "
              f"max DD median {np.median(dd):.0%} worst {dd.max():.0%} | taken {med['taken']}, "
              f"skipped full {med['skipped_full']}, below min {med['skipped_min']} | win {med['win']:.0f}%{tag}")
        print(f"        years (median seed, USDT): {med['years']}  positive {ypos}/{len(med['years'])}")
        if K == 5:
            ok = np.median(fin) > 300 and ypos >= 4 and np.median(dd) < 0.40
            print(f"        useful for 300 USDT (pre-set rule): {'YES' if ok else 'NO'}")


def main():
    minn = min_notionals()
    oos = engine_trades(D.oos_files())
    oos.to_parquet(OUT / "channel_trades_unseen.parquet")
    report("UNSEEN coins (main)", oos, minn)
    dev = engine_trades(D.dev_files())
    report("development coins (in-sample, comparison)", dev, minn)


if __name__ == "__main__":
    main()
