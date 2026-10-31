"""Validation gate for the four volatility_breakout survivors.

Every test the project applies, on the expanded universe, at full strictness:

  walk-forward (selection re-run in-fold)   cost x2      slippage x2
  funding x2                                long/short   regime
  original-16 vs unseen coins               portfolio-level with real limits

Two return numbers are reported throughout, because they answer different
questions and conflating them overstates everything:

  aggregate/pair  - sum of per-pair P&L over a nominal 1000. The engine
                    simulates each pair independently with NO portfolio cap, so
                    on 70 coins this silently assumes ~70x the capital. Useful
                    only for comparing candidates against each other.
  portfolio       - the same trades replayed through one account: a hard cap on
                    concurrent positions, stake = equity / max_concurrent, a
                    trade skipped when the book is full. This is the number a
                    person could actually have earned.
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
import backtest as bt                                  # noqa: E402
from backtest import Config, simulate                  # noqa: E402
from features import load_pair                         # noqa: E402

UNI = ROOT / "data" / "market" / "universe"
OUT = HERE / "engine_results" / "gate_results.json"
WALLET = 1000.0
ORIGINAL_16 = {"BTC", "ETH", "SOL", "XRP", "LINK", "LTC", "ADA", "AVAX",
               "DOGE", "DOT", "ATOM", "UNI", "BCH", "ETC", "TRX", "NEAR"}

CANDIDATES = [
    ("volatility_breakout_b2|btc|both", "volatility_breakout", ["btc_regime"], "both", {"bars": 2, "atr_mult": 2.0}),
    ("volatility_breakout_b2|btc+vol|both", "volatility_breakout", ["btc_regime", "volume"], "both", {"bars": 2, "atr_mult": 2.0}),
    ("volatility_breakout_b4|btc|both", "volatility_breakout", ["btc_regime"], "both", {"bars": 4, "atr_mult": 2.0}),
    ("volatility_breakout_b4|btc+vol|both", "volatility_breakout", ["btc_regime", "volume"], "both", {"bars": 4, "atr_mult": 2.0}),
]
# the harvested families, carried along to test the hypothesis that they are
# the less robust ones rather than assuming it
CONTROLS = [
    ("trend_resume|btc|long", "trend_resume", ["btc_regime"], "long", {}),
    ("rsi_reset|btc|long", "rsi_reset", ["btc_regime"], "long", {}),
    ("vwap_reversion|btc|long", "vwap_reversion", ["btc_regime"], "long", {}),
    ("failed_breakout|btc|long", "failed_breakout", ["btc_regime"], "long", {}),
]
REGIMES = [("bull2021", "2021-01-01", "2021-11-10"),
           ("bear2022", "2021-11-10", "2023-01-01"),
           ("recovery2023_24", "2023-01-01", "2025-01-01"),
           ("recent2025_26", "2025-01-01", "2026-10-01")]
FOLDS = [("2021-01-01", "2022-07-01", "2023-01-01"), ("2021-07-01", "2023-01-01", "2023-07-01"),
         ("2022-01-01", "2023-07-01", "2024-01-01"), ("2022-07-01", "2024-01-01", "2024-07-01"),
         ("2023-01-01", "2024-07-01", "2025-01-01"), ("2023-07-01", "2025-01-01", "2025-07-01"),
         ("2024-01-01", "2025-07-01", "2026-01-01"), ("2024-07-01", "2026-01-01", "2026-10-01")]
CFG = dict(leverage=1.0, stop_mode="atr", stop_atr=2.0, tp_mode="none",
           tp_atr=(), tp_frac=(), entry_mode="instant")


def ts(x):
    return pd.Timestamp(x, tz="UTC")


def load_set(name):
    split = json.loads((UNI / "split_140.json").read_text(encoding="utf-8"))
    uni, unavailable = {}, []
    for c in split[name]:
        f = load_pair(c, futures=True)
        if f is None or len(f.close) < 400:
            unavailable.append(c)
        else:
            uni[c] = f
    return uni, unavailable


def trades_df(uni, spec):
    tr = simulate(uni, spec, Config(**CFG))
    if not tr:
        return pd.DataFrame()
    rows = [{"pair": t.pair, "pnl": t.pnl, "notional": t.notional,
             "side": "long" if t.side > 0 else "short",
             "entry": pd.Timestamp(uni[t.pair].date[t.entry_i]),
             "exit": pd.Timestamp(uni[t.pair].date[min(t.exit_i, len(uni[t.pair].date) - 1)]),
             "funding": t.funding_paid} for t in tr]
    df = pd.DataFrame(rows)
    df["entry"] = pd.to_datetime(df.entry, utc=True)
    df["exit"] = pd.to_datetime(df.exit, utc=True)
    return df


def agg_stats(df):
    if df.empty:
        return {"trades": 0, "ret_pct": 0.0, "pf": None}
    w, l = df[df.pnl > 0].pnl.sum(), -df[df.pnl < 0].pnl.sum()
    return {"trades": int(len(df)), "ret_pct": round(df.pnl.sum() / WALLET * 100, 1),
            "pf": round(w / l, 3) if l > 0 else None}


def portfolio(df, max_concurrent=10, equity0=WALLET):
    """Replay the same trades through ONE account with a hard concurrency cap.

    Stake is equity/max_concurrent, so the book is fully deployed at the cap and
    a signal arriving on a full book is skipped, exactly as a live bot would.
    Returns realistic return, max drawdown and how many signals were refused.
    """
    if df.empty:
        return {"ret_pct": 0.0, "taken": 0, "skipped": 0, "max_dd": 0.0}
    import heapq
    d = df.sort_values("entry").reset_index(drop=True)
    equity, peak, maxdd = equity0, equity0, 0.0
    book: list = []          # heap of (exit_time, scaled_pnl) for open trades
    taken = skipped = 0
    for _, t in d.iterrows():
        # realise everything that closed at or before this entry, in close order,
        # marking drawdown against the running peak as each one lands
        while book and book[0][0] <= t.entry:
            _, scaled = heapq.heappop(book)
            equity += scaled
            peak = max(peak, equity)
            if peak > 0:
                maxdd = max(maxdd, (peak - equity) / peak * 100)
        if len(book) >= max_concurrent:
            skipped += 1
            continue
        stake = equity / max_concurrent          # compounds with the account
        scaled = t.pnl / t.notional * stake if t.notional else 0.0
        heapq.heappush(book, (t.exit, scaled))
        taken += 1
    while book:
        _, scaled = heapq.heappop(book)
        equity += scaled
        peak = max(peak, equity)
        if peak > 0:
            maxdd = max(maxdd, (peak - equity) / peak * 100)
    return {"ret_pct": round((equity / equity0 - 1) * 100, 1), "taken": taken,
            "skipped": skipped, "max_dd": round(maxdd, 1),
            "final_equity": round(equity, 1)}


def run_variant(uni, spec, fee_mult=1.0, slip_mult=1.0, funding_mult=1.0):
    of, os_ = bt.FEE, bt.SLIP
    bt.FEE, bt.SLIP = of * fee_mult, os_ * slip_mult
    saved = {}
    if funding_mult != 1.0:
        for k, f in uni.items():
            saved[k] = f.funding
            f.funding = f.funding * funding_mult
    try:
        return trades_df(uni, spec)
    finally:
        bt.FEE, bt.SLIP = of, os_
        for k, v in saved.items():
            uni[k].funding = v


def main():
    dev, dev_na = load_set("dev")
    hold, hold_na = load_set("holdout")
    print(f"dev {len(dev)} coins (unavailable {len(dev_na)}: {' '.join(dev_na) or 'none'})")
    print(f"holdout {len(hold)} coins (unavailable {len(hold_na)}: {' '.join(hold_na) or 'none'})\n", flush=True)

    res = {"unavailable": {"dev": dev_na, "holdout": hold_na}, "candidates": {}}
    allc = CANDIDATES + CONTROLS

    print("=" * 118)
    print(f"{'candidate':38}{'set':9}{'agg ret%':>10}{'PF':>7}{'2x cost PF':>12}"
          f"{'slip2x PF':>11}{'fund2x PF':>11}{'pf ret%':>9}{'pf DD%':>8}{'skip%':>7}")
    print("=" * 118)
    for cid, fam, filts, direction, params in allc:
        spec = {"family": fam, "direction": direction, "filters": filts,
                "trend_mode": "with", "params": params}
        entry = {}
        for setname, uni in (("dev", dev), ("holdout", hold)):
            base = run_variant(uni, spec)
            c2 = run_variant(uni, spec, fee_mult=2.0, slip_mult=2.0)
            s2 = run_variant(uni, spec, slip_mult=2.0)
            f2 = run_variant(uni, spec, funding_mult=2.0)
            pf10 = portfolio(base, 10)
            a = agg_stats(base)
            e = {"aggregate": a,
                 "cost2x": agg_stats(c2), "slip2x": agg_stats(s2), "funding2x": agg_stats(f2),
                 "portfolio_10": pf10, "portfolio_20": portfolio(base, 20),
                 "long_pnl": round(base[base.side == "long"].pnl.sum(), 1) if not base.empty else 0,
                 "short_pnl": round(base[base.side == "short"].pnl.sum(), 1) if not base.empty else 0,
                 "long_trades": int((base.side == "long").sum()) if not base.empty else 0,
                 "short_trades": int((base.side == "short").sum()) if not base.empty else 0,
                 "funding_paid": round(base.funding.sum(), 1) if not base.empty else 0}
            for n, s, en in REGIMES:
                sub = base[(base.entry >= ts(s)) & (base.entry < ts(en))]
                e[n] = round(sub.pnl.sum() / WALLET * 100, 1)
            if setname == "holdout" and not base.empty:
                o = base[base.pair.isin(ORIGINAL_16)]
                n_ = base[~base.pair.isin(ORIGINAL_16)]
                e["original16"] = {"coins": int(o.pair.nunique()), **agg_stats(o)}
                e["unseen"] = {"coins": int(n_.pair.nunique()), **agg_stats(n_)}
            entry[setname] = e
            skip = pf10["skipped"] / max(1, pf10["skipped"] + pf10["taken"]) * 100
            print(f"{cid:38}{setname:9}{a['ret_pct']:>10}{a['pf'] or 0:>7}"
                  f"{e['cost2x']['pf'] or 0:>12}{e['slip2x']['pf'] or 0:>11}"
                  f"{e['funding2x']['pf'] or 0:>11}{pf10['ret_pct']:>9}{pf10['max_dd']:>8}{skip:>6.0f}%",
                  flush=True)
        res["candidates"][cid] = entry

    # ---- walk-forward with selection re-run inside each fold ----
    print("\n" + "=" * 118)
    print("WALK-FORWARD on the expanded universe (selection re-run per fold, dev coins)")
    print("=" * 118)
    cache = {}
    for cid, fam, filts, direction, params in allc:
        spec = {"family": fam, "direction": direction, "filters": filts,
                "trend_mode": "with", "params": params}
        cache[cid] = run_variant(dev, spec)
    folds, total = [], 0.0
    for a, split, b in FOLDS:
        best, bestr = None, -1e9
        for cid, df in cache.items():
            tr = df[(df.entry >= ts(a)) & (df.entry < ts(split))]
            if len(tr) < 30:
                continue
            r = tr.pnl.sum() / WALLET * 100
            if r > bestr:
                best, bestr = cid, r
        oos = cache[best][(cache[best].entry >= ts(split)) & (cache[best].entry < ts(b))]
        o = oos.pnl.sum() / WALLET * 100
        pf_oos = portfolio(oos, 10)
        total += o
        folds.append({"oos": f"{split}->{b}", "picked": best, "train_ret": round(bestr, 1),
                      "oos_ret": round(o, 1), "oos_portfolio_ret": pf_oos["ret_pct"],
                      "oos_trades": int(len(oos))})
        print(f"  oos {split[:7]}->{b[:7]}  {best:38} train {round(bestr,1):>8}  "
              f"OOS agg {round(o,1):>8}  OOS portfolio {pf_oos['ret_pct']:>7}%  ({len(oos)} tr)", flush=True)
    pos = sum(1 for f in folds if f["oos_ret"] > 0)
    posp = sum(1 for f in folds if f["oos_portfolio_ret"] > 0)
    res["walkforward"] = {"folds": folds, "oos_sum": round(total, 1),
                          "folds_positive": f"{pos}/{len(FOLDS)}",
                          "folds_positive_portfolio": f"{posp}/{len(FOLDS)}"}
    print(f"\n  OOS sum {total:+.1f}%   folds positive {pos}/{len(FOLDS)}   "
          f"(portfolio-level {posp}/{len(FOLDS)})")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(f"\nwrote {OUT}")
    print("GATE_RUN_COMPLETE")


if __name__ == "__main__":
    main()
