"""Deliver two working strategies: one for spot, one for futures.

Objective here is different from the tournament's. The tournament hunted for the
largest robust edge and rejected almost everything. This asks a narrower,
practical question:

  * SPOT  -- long only (you cannot short spot). Steady participation, modest
    profit, capital actually deployed.
  * FUTURES -- long and short both contributing meaningfully, not shorts as a
    token 5% of P&L.

Selection favours consistency and balance over headline profit factor. Nothing
is disqualified for being merely decent.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest import Config, simulate                           # noqa: E402
from features import DEV_COINS, HOLDOUT_COINS, load_universe    # noqa: E402
from tournament import SPAN_YEARS, metrics, period_consistency  # noqa: E402

BASE = {"family": "volatility_breakout", "direction": "both"}


def run(uni, spec, cfg):
    tr = simulate(uni, spec, cfg)
    m = metrics(tr)
    c, buckets = period_consistency(tr, uni)
    m["consistency"] = round(c, 3)
    m["buckets"] = buckets
    return m, tr


def fmt(tag, m):
    return (f"{tag:52} {m['trades']/SPAN_YEARS:>5.0f}/yr  ret {m['ret_pct']:>7.1f}%  "
            f"PF {m['pf']:>5.2f}  DD {m['max_dd']:>5.1f}%  cons {m['consistency']:.2f}  "
            f"L {m.get('long_pct', 0):>7.1f}% / S {m.get('short_pct', 0):>6.1f}%")


# ---------------------------------------------------------------- SPOT
def spot_search(dev, hold):
    print("=" * 110)
    print("SPOT  (long only -- shorting is not possible on spot)")
    print("=" * 110, flush=True)
    results = []
    for bars in (2, 3, 4, 6):
        for mult in (1.5, 2.0, 2.5):
            for filt, name in (([], "nofilt"), (["btc_regime"], "btc"),
                               (["volume"], "vol"), (["btc_regime", "volume"], "btc+vol")):
                for stop, sname in ((2.0, "atr2"), (3.0, "atr3"), (8.0, "wide")):
                    spec = {**BASE, "filters": filt, "trend_mode": "with",
                            "direction": "long",
                            "params": {"bars": bars, "atr_mult": mult}}
                    cfg = Config(leverage=1.0, stop_mode="atr", stop_atr=stop,
                                 tp_mode="none", tp_atr=(), tp_frac=(),
                                 entry_mode="instant")
                    m, _ = run(dev, spec, cfg)
                    if m["trades"] < 300 or m["ret_pct"] <= 0:
                        continue
                    results.append((m, spec, cfg,
                                    f"bars{bars}_m{mult}_{name}_{sname}"))
    # rank by consistency first, then return -- steady beats spiky
    results.sort(key=lambda r: (-r[0]["consistency"], -r[0]["ret_pct"]))
    print(f"{len(results)} spot configs profitable; top 6 by consistency:")
    for m, spec, cfg, tag in results[:6]:
        print("  " + fmt(tag, m), flush=True)
    if not results:
        return None
    best = results[0]
    hm, _ = run(hold, best[1], best[2])
    print("\n  SPOT PICK : " + best[3])
    print("  " + fmt("dev", best[0]))
    print("  " + fmt("holdout (unseen coins)", hm))
    print("  half-years:", best[0]["buckets"])
    return best


# ---------------------------------------------------------------- FUTURES
def futures_search(dev, hold):
    print("\n" + "=" * 110)
    print("FUTURES  (long and short, aiming for balanced contribution)")
    print("=" * 110, flush=True)
    short_gates = {
        "all":            None,
        "weakdn":         ["weak_down", "range"],
        "weakdn+strong":  ["weak_down", "range", "strong_down"],
        "downonly":       ["weak_down", "strong_down"],
    }
    results = []
    for bars in (2, 3, 4):
        for mult in (1.5, 2.0, 2.5):
            for gname, gate in short_gates.items():
                for stop, sname in ((2.0, "atr2"), (3.0, "atr3")):
                    spec = {**BASE, "filters": ["btc_regime"], "trend_mode": "with",
                            "params": {"bars": bars, "atr_mult": mult}}
                    if gate:
                        spec["short_regime"] = gate
                    cfg = Config(leverage=1.0, stop_mode="atr", stop_atr=stop,
                                 tp_mode="none", tp_atr=(), tp_frac=(),
                                 entry_mode="instant")
                    m, _ = run(dev, spec, cfg)
                    if m["trades"] < 300 or m["ret_pct"] <= 0 or m["liquidations"]:
                        continue
                    tot = abs(m["long_pct"]) + abs(m["short_pct"])
                    share = m["short_pct"] / tot if tot else 0
                    m["short_share"] = round(share, 3)
                    results.append((m, spec, cfg,
                                    f"bars{bars}_m{mult}_sh-{gname}_{sname}"))
    # want shorts pulling real weight AND the whole thing profitable
    bal = [r for r in results if r[0]["short_share"] >= 0.20]
    print(f"{len(results)} futures configs profitable, "
          f"{len(bal)} with shorts >= 20% of gross P&L")
    pool = bal or results
    pool.sort(key=lambda r: (-(r[0]["short_share"] * 0.5 + r[0]["consistency"] * 0.5),
                             -r[0]["ret_pct"]))
    print("top 6 by short-balance + consistency:")
    for m, spec, cfg, tag in pool[:6]:
        print("  " + fmt(tag, m) + f"  shortShare {m['short_share']:.0%}", flush=True)
    if not pool:
        return None
    best = pool[0]
    hm, _ = run(hold, best[1], best[2])
    print("\n  FUTURES PICK : " + best[3])
    print("  " + fmt("dev", best[0]))
    print("  " + fmt("holdout (unseen coins)", hm))
    print("  half-years:", best[0]["buckets"])
    return best


if __name__ == "__main__":
    spot_dev = load_universe(DEV_COINS, futures=False)
    spot_hold = load_universe(HOLDOUT_COINS, futures=False)
    fut_dev = load_universe(DEV_COINS)
    fut_hold = load_universe(HOLDOUT_COINS)
    spot_search(spot_dev, spot_hold)
    futures_search(fut_dev, fut_hold)
    print("\ndone", flush=True)
