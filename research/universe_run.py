"""Run the strategy library across the 140-coin universe.

The question: do the strategies we already have generalize beyond the 16 coins
they were found on, or were those 16 the edge?

Discipline preserved from the 16-coin work:
  * the universe was fixed BEFORE this run and is not touched by its results
  * dev/holdout is drawn by RULE (alternating market-cap rank), not by hand
  * selection inside walk-forward folds, so a leader is never scored on the
    history that chose it
  * one simulation per combination; every breakdown is derived from those trades

Resumable: each combination appends to universe_ledger.jsonl when it finishes,
so a killed run continues instead of restarting.

    python universe_run.py                 # dev coins, full grid
    python universe_run.py --holdout       # same grid on the holdout coins
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "engine"))
from backtest import Config, simulate            # noqa: E402
from features import load_pair                   # noqa: E402

UNI = ROOT / "data" / "market" / "universe"
LEDGER = HERE / "universe_ledger.jsonl"
TRADES = HERE / "universe_trades"

# The candidates that already exist, not a fresh search: the delivered
# volatility_breakout picks plus the families harvested and added since.
GRID = [
    ("volatility_breakout", {"bars": 2, "atr_mult": 2.0}),
    ("volatility_breakout", {"bars": 4, "atr_mult": 2.0}),
    ("trend_resume", {}),
    ("rsi_reset", {}),
    ("vwap_reversion", {}),
    ("failed_breakout", {}),
]
FILTERS = {"btc": ["btc_regime"], "btc+vol": ["btc_regime", "volume"]}
DIRECTIONS = ["long", "both"]

REGIMES = [("bull2021", "2021-01-01", "2021-11-10"),
           ("bear2022", "2021-11-10", "2023-01-01"),
           ("recovery2023_24", "2023-01-01", "2025-01-01"),
           ("recent2025_26", "2025-01-01", "2026-10-01")]
WALLET = 1000.0


def ts(x):
    return pd.Timestamp(x, tz="UTC")


def load_universe_coins(holdout: bool):
    split = json.loads((UNI / "split_140.json").read_text(encoding="utf-8"))
    wanted = split["holdout" if holdout else "dev"]
    uni, missing = {}, []
    for c in wanted:
        f = load_pair(c, futures=True)
        if f is None or len(f.close) < 400:
            missing.append(c)
            continue
        uni[c] = f
    return uni, missing, split["rule"]


def done_keys():
    if not LEDGER.exists():
        return set()
    out = set()
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
            out.add((e["cid"], e["set"]))
        except Exception:
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", action="store_true")
    a = ap.parse_args()
    setname = "holdout" if a.holdout else "dev"

    uni, missing, rule = load_universe_coins(a.holdout)
    print(f"set={setname}  coins with data: {len(uni)}   missing: {len(missing)}")
    if missing:
        print(f"  no data: {' '.join(missing[:20])}{' …' if len(missing) > 20 else ''}")
    print(f"  split rule: {rule}\n", flush=True)

    TRADES.mkdir(exist_ok=True)
    seen = done_keys()
    cfg = Config(leverage=1.0, stop_mode="atr", stop_atr=2.0, tp_mode="none",
                 tp_atr=(), tp_frac=(), entry_mode="instant")

    print(f"{'combination':46}{'trades':>8}{'ret%':>9}{'PF':>7}{'coins+':>8}{'secs':>7}", flush=True)
    for fam, params in GRID:
        ptag = f"_b{params['bars']}" if "bars" in params else ""
        for fname, filts in FILTERS.items():
            for direction in DIRECTIONS:
                cid = f"{fam}{ptag}|{fname}|{direction}"
                if (cid, setname) in seen:
                    continue
                spec = {"family": fam, "direction": direction, "filters": filts,
                        "trend_mode": "with", "params": params}
                t0 = time.time()
                tr = simulate(uni, spec, cfg)
                secs = round(time.time() - t0)
                if not tr:
                    rec = {"cid": cid, "set": setname, "trades": 0, "status": "no_trades",
                           "secs": secs}
                else:
                    rows = [{"pair": t.pair, "pnl": t.pnl,
                             "side": "long" if t.side > 0 else "short",
                             "entry_date": pd.Timestamp(uni[t.pair].date[t.entry_i])}
                            for t in tr]
                    df = pd.DataFrame(rows)
                    df["entry_date"] = pd.to_datetime(df.entry_date, utc=True)
                    df.to_parquet(TRADES / f"{cid.replace('|', '~')}__{setname}.parquet")
                    per_pair = df.groupby("pair").pnl.sum()
                    gross_w = df[df.pnl > 0].pnl.sum()
                    gross_l = -df[df.pnl < 0].pnl.sum()
                    rec = {"cid": cid, "set": setname, "family": fam, "filters": fname,
                           "direction": direction, "status": "ok",
                           "trades": int(len(df)),
                           "ret_pct": round(df.pnl.sum() / WALLET * 100, 2),
                           "pf": round(gross_w / gross_l, 3) if gross_l > 0 else None,
                           "coins_traded": int(per_pair.size),
                           "coins_profitable": int((per_pair > 0).sum()),
                           "long_pnl": round(df[df.side == "long"].pnl.sum(), 1),
                           "short_pnl": round(df[df.side == "short"].pnl.sum(), 1),
                           "long_trades": int((df.side == "long").sum()),
                           "short_trades": int((df.side == "short").sum()),
                           "secs": secs}
                    for n, s, e in REGIMES:
                        sub = df[(df.entry_date >= ts(s)) & (df.entry_date < ts(e))]
                        rec[n] = round(sub.pnl.sum() / WALLET * 100, 1)
                        rec[n + "_tr"] = int(len(sub))
                with open(LEDGER, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, default=float) + "\n")
                print(f"{cid:46}{rec.get('trades',0):>8}{rec.get('ret_pct',0):>9}"
                      f"{rec.get('pf') or 0:>7}"
                      f"{rec.get('coins_profitable',0)}/{rec.get('coins_traded',0):<6}{secs:>7}",
                      flush=True)
    print("UNIVERSE_RUN_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
