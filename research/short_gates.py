"""The full gate ladder for the nine dedicated short families.

Same standards as the long candidate, no exceptions: dev screen, coin holdout,
2x costs, 2x slippage, regime split with bear2022 called out, and portfolio-level
return/drawdown. Short families are short-only by construction, so `direction`
is not a variable here.

The prior on these is unfavourable and stated up front: every mirrored short leg
tested so far loses outright and only pays in bear2022. The question is whether
short-SPECIFIC structure does better than a mirrored long, not whether shorts can
be made to look good.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "engine"))
import backtest as bt                              # noqa: E402
from backtest import Config, simulate              # noqa: E402
from features import load_pair                     # noqa: E402
from gate_run import CFG, portfolio, ts            # noqa: E402

UNI = ROOT / "data" / "market" / "universe"
OUT = HERE / "engine_results" / "short_gates.json"
WALLET = 1000.0

SHORTS = ["breakdown", "resistance_rejection", "breakdown_retest", "vwap_rejection",
          "lower_high", "bear_trend_continuation", "bear_divergence",
          "volume_breakdown", "downside_vol_expansion"]
# the incumbent to beat: the mirrored short leg of the validated long candidate
BASELINE = ("vb_b4_shortleg", "volatility_breakout", ["btc_regime", "volume"],
            {"bars": 4, "atr_mult": 2.0}, "short")
FILTERS = {"nofilt": [], "btc": ["btc_regime"], "btc+vol": ["btc_regime", "volume"]}
REGIMES = [("bull2021", "2021-01-01", "2021-11-10"), ("bear2022", "2021-11-10", "2023-01-01"),
           ("recovery2023_24", "2023-01-01", "2025-01-01"), ("recent2025_26", "2025-01-01", "2026-10-01")]


def load(setname):
    split = json.loads((UNI / "split_140.json").read_text(encoding="utf-8"))
    uni = {}
    for c in split[setname]:
        f = load_pair(c, futures=True)
        if f is not None and len(f.close) >= 400:
            uni[c] = f
    return uni


def run(uni, spec, fee=1.0, slip=1.0):
    of, os_ = bt.FEE, bt.SLIP
    bt.FEE, bt.SLIP = of * fee, os_ * slip
    try:
        tr = simulate(uni, spec, Config(**CFG))
    finally:
        bt.FEE, bt.SLIP = of, os_
    if not tr:
        return pd.DataFrame()
    rows = [{"pair": t.pair, "pnl": t.pnl, "notional": t.notional,
             "entry": pd.Timestamp(uni[t.pair].date[t.entry_i]),
             "exit": pd.Timestamp(uni[t.pair].date[min(t.exit_i, len(uni[t.pair].date) - 1)])}
            for t in tr]
    d = pd.DataFrame(rows)
    for c in ("entry", "exit"):
        d[c] = pd.to_datetime(d[c], utc=True)
    return d


def stats(d):
    if d.empty:
        return {"trades": 0, "ret": 0.0, "pf": None, "coins": 0, "coins_prof": 0}
    w, l = d[d.pnl > 0].pnl.sum(), -d[d.pnl < 0].pnl.sum()
    per = d.groupby("pair").pnl.sum()
    return {"trades": int(len(d)), "ret": round(d.pnl.sum() / WALLET * 100, 1),
            "pf": round(w / l, 3) if l else None, "coins": int(per.size),
            "coins_prof": int((per > 0).sum())}


def main():
    dev, hold = load("dev"), load("holdout")
    print(f"dev {len(dev)} coins | holdout {len(hold)} coins\n", flush=True)
    combos = [(f"{fam}|{fn}", fam, fl, {}, "short") for fam in SHORTS for fn, fl in FILTERS.items()]
    combos.append((f"{BASELINE[0]}|{BASELINE[2] and 'btc+vol'}", BASELINE[1], BASELINE[2],
                   BASELINE[3], BASELINE[4]))

    res = {}
    print("=" * 122)
    print(f"{'short candidate':40}{'trades':>8}{'dev ret%':>10}{'dev PF':>8}"
          f"{'hold PF':>9}{'2x cost':>9}{'bear22':>9}{'recent':>9}{'pf ret%':>9}{'pf DD%':>8}")
    print("=" * 122)
    for cid, fam, filts, params, direction in combos:
        spec = {"family": fam, "direction": direction, "filters": filts,
                "trend_mode": "with", "params": params}
        d = run(dev, spec)
        if d.empty:
            print(f"{cid:40}  NO TRADES"); res[cid] = {"status": "no_trades"}; continue
        h = run(hold, spec)
        c2 = run(dev, spec, fee=2.0, slip=2.0)
        s2 = run(dev, spec, slip=2.0)
        p = portfolio(d, 10)
        e = {"dev": stats(d), "holdout": stats(h), "cost2x": stats(c2), "slip2x": stats(s2),
             "portfolio_10": p}
        for n, a, b in REGIMES:
            e[n] = round(d[(d.entry >= ts(a)) & (d.entry < ts(b))].pnl.sum() / WALLET * 100, 1)
        res[cid] = e
        print(f"{cid:40}{e['dev']['trades']:>8}{e['dev']['ret']:>10}{e['dev']['pf'] or 0:>8}"
              f"{e['holdout']['pf'] or 0:>9}{e['cost2x']['pf'] or 0:>9}"
              f"{e['bear2022']:>9}{e['recent2025_26']:>9}{p['ret_pct']:>9}{p['max_dd']:>8}",
              flush=True)

    # ---- gate verdicts, same thresholds as the long candidate ----
    print("\n" + "=" * 122)
    print("GATE VERDICTS (holdout PF > 1.0 AND survives 2x costs AND positive in bear2022)")
    print("=" * 122)
    survivors = []
    for cid, e in res.items():
        if e.get("status") == "no_trades":
            continue
        hpf = e["holdout"]["pf"] or 0
        cpf = e["cost2x"]["pf"] or 0
        ok = hpf > 1.0 and cpf > 1.0 and e["bear2022"] > 0
        why = []
        if hpf <= 1.0:
            why.append(f"holdout PF {hpf}")
        if cpf <= 1.0:
            why.append(f"2x-cost PF {cpf}")
        if e["bear2022"] <= 0:
            why.append(f"bear2022 {e['bear2022']}")
        print(f"  {cid:40} {'PASS' if ok else 'FAIL':5} {'; '.join(why)}")
        if ok:
            survivors.append(cid)
    print(f"\n  survivors: {len(survivors)}/{len([1 for e in res.values() if e.get('status')!='no_trades'])}"
          f"  {survivors}")
    OUT.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(f"\nwrote {OUT}\nSHORT_GATES_COMPLETE")


if __name__ == "__main__":
    main()
