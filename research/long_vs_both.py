"""Gate 3: does the short leg earn its keep?

The short leg of vb_b4 loses -711.7 over 1811 trades on holdout, so it can only
be justified by risk reduction. This measures exactly that: the same family, the
same coins, the same costs, long-only against long+short, at PORTFOLIO level
where drawdown is a real quantity.

Decision rule, fixed here before the numbers are seen: the short leg is worth
carrying only if it improves return/drawdown (a crude Calmar) on the HOLDOUT
set. If long-only is better on both return and drawdown, trade long-only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "engine"))
from backtest import Config, simulate            # noqa: E402
from features import load_pair                   # noqa: E402
from gate_run import CFG, portfolio, ts          # noqa: E402

UNI = ROOT / "data" / "market" / "universe"
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


def run(uni, direction):
    spec = {"family": "volatility_breakout", "direction": direction,
            "filters": ["btc_regime", "volume"], "trend_mode": "with",
            "params": {"bars": 4, "atr_mult": 2.0}}
    tr = simulate(uni, spec, Config(**CFG))
    rows = [{"pnl": t.pnl, "notional": t.notional,
             "entry": pd.Timestamp(uni[t.pair].date[t.entry_i]),
             "exit": pd.Timestamp(uni[t.pair].date[min(t.exit_i, len(uni[t.pair].date) - 1)])}
            for t in tr]
    d = pd.DataFrame(rows)
    for c in ("entry", "exit"):
        d[c] = pd.to_datetime(d[c], utc=True)
    return d


def main():
    out = {}
    for setname in ("dev", "holdout"):
        uni = load(setname)
        print(f"\n{'='*104}\n{setname.upper()}  ({len(uni)} coins)\n{'='*104}")
        print(f"{'variant':12}{'trades':>8}{'agg ret%':>10}{'PF':>7}"
              f"{'pf ret%':>10}{'pf DD%':>9}{'calmar':>9}{'taken':>8}{'skip%':>7}")
        rows = {}
        for direction in ("long", "both"):
            d = run(uni, direction)
            w, l = d[d.pnl > 0].pnl.sum(), -d[d.pnl < 0].pnl.sum()
            p = portfolio(d, 10)
            cal = p["ret_pct"] / p["max_dd"] if p["max_dd"] > 0 else None
            rows[direction] = {"trades": int(len(d)),
                               "agg_ret": round(d.pnl.sum() / 10, 1),
                               "pf": round(w / l, 3) if l else None,
                               "portfolio_ret": p["ret_pct"], "max_dd": p["max_dd"],
                               "calmar": round(cal, 2) if cal else None,
                               "taken": p["taken"], "skipped": p["skipped"]}
            for n, a, b in REGIMES:
                s = d[(d.entry >= ts(a)) & (d.entry < ts(b))]
                sp = portfolio(s, 10)
                rows[direction][n] = sp["ret_pct"]
                rows[direction][n + "_dd"] = sp["max_dd"]
            r = rows[direction]
            skip = r["skipped"] / max(1, r["skipped"] + r["taken"]) * 100
            print(f"{direction:12}{r['trades']:>8}{r['agg_ret']:>10}{r['pf'] or 0:>7}"
                  f"{r['portfolio_ret']:>10}{r['max_dd']:>9}{r['calmar'] or 0:>9}"
                  f"{r['taken']:>8}{skip:>6.0f}%", flush=True)
        print(f"\n  portfolio return by regime (10 slots):")
        print(f"  {'variant':12}" + "".join(f"{n:>20}" for n, _, _ in REGIMES))
        for direction in ("long", "both"):
            print(f"  {direction:12}" + "".join(
                f"{rows[direction][n]:>13}{'/'}{rows[direction][n+'_dd']:>5}" for n, _, _ in REGIMES))
        print("   (return / max DD per regime)")
        out[setname] = rows

    h = out["holdout"]
    print(f"\n{'='*104}\nDECISION (holdout, declared before the run: better on BOTH return and DD wins)\n{'='*104}")
    print(f"  long-only : ret {h['long']['portfolio_ret']:>8}%  DD {h['long']['max_dd']:>6}%  calmar {h['long']['calmar']}")
    print(f"  long+short: ret {h['both']['portfolio_ret']:>8}%  DD {h['both']['max_dd']:>6}%  calmar {h['both']['calmar']}")
    bw = "long+short" if (h["both"]["calmar"] or 0) > (h["long"]["calmar"] or 0) else "long-only"
    print(f"  -> better risk-adjusted: {bw}")
    worst_l = min(h["long"][n] for n, _, _ in REGIMES)
    worst_b = min(h["both"][n] for n, _, _ in REGIMES)
    print(f"  worst regime: long-only {worst_l}%   long+short {worst_b}%")
    (HERE / "engine_results" / "long_vs_both.json").write_text(
        json.dumps(out, indent=1, default=float), encoding="utf-8")
    print("\nLONG_VS_BOTH_COMPLETE")


if __name__ == "__main__":
    main()
