"""What does each filter actually remove, and does it earn its place?

Items 1 and 2 of the frequency brief: which filters eliminate the most
otherwise-profitable trades, and are any of them redundant?

The test is subtraction, not argument. Run the identical spec with each filter
removed and compare. A filter earns its place if removing it raises trade count
but LOWERS profit factor and expectancy - that is the filter doing its job. A
filter that can be removed with no cost to either is redundant.

Every variant is scored at the live book size (20 slots + the same-direction
cap), because a filter that only adds refused signals has changed nothing.

    python research/filter_attribution.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "engine"))
from backtest import Config, simulate_pair   # noqa: E402
from frequency_baseline import LIVE_CFG, live_universe, load  # noqa: E402
from slot_sensitivity import MAX_SAME_DIRECTION, replay       # noqa: E402

VARIANTS = {
    "LIVE  btc_regime + volume": ["btc_regime", "volume"],
    "drop volume":               ["btc_regime"],
    "drop btc_regime":           ["volume"],
    "no filters at all":         [],
}


def stats(df: pd.DataFrame, yrs: float) -> dict:
    w = df[df.pnl > 0].pnl.sum()
    l = -df[df.pnl < 0].pnl.sum()
    return {
        "trades": len(df), "per_year": len(df) / yrs,
        "pf": w / l if l > 0 else float("inf"),
        "expectancy": df.pnl.mean(),
        "win_pct": (df.pnl > 0).mean() * 100,
        "net": df.pnl.sum(),
    }


def main() -> int:
    uni, _ = load(live_universe())
    cfg = Config(**LIVE_CFG)
    results = {}

    for label, filters in VARIANTS.items():
        spec = {"family": "volatility_breakout", "direction": "both",
                "filters": filters, "trend_mode": "with",
                "params": {"bars": 4, "atr_mult": 2.0}}
        rows = []
        for pair, f in uni.items():
            for t in simulate_pair(f, spec, cfg, pair):
                rows.append({"pair": pair, "side": "long" if t.side > 0 else "short",
                             "pnl": t.pnl,
                             "entry": pd.Timestamp(f.date[t.entry_i]),
                             "exit": pd.Timestamp(f.date[t.exit_i])})
        df = pd.DataFrame(rows)
        df["entry"] = pd.to_datetime(df.entry, utc=True)
        df["exit"] = pd.to_datetime(df.exit, utc=True)
        yrs = (df.entry.max() - df.entry.min()).days / 365.25
        taken, _, _ = replay(df.to_dict("records"), 20, MAX_SAME_DIRECTION)
        results[label] = {"raw": stats(df, yrs), "live": stats(pd.DataFrame(taken), yrs)}
        print(f"  {label:<28} done  ({len(df):,} raw signals)", flush=True)

    base_raw = results["LIVE  btc_regime + volume"]["raw"]
    base_live = results["LIVE  btc_regime + volume"]["live"]

    print()
    print("=" * 96)
    print("  RAW SIGNAL STREAM (before the book refuses anything)")
    print("=" * 96)
    print(f"{'variant':<28}{'signals/yr':>12}{'vs live':>10}{'PF':>8}"
          f"{'expectancy':>13}{'win%':>8}{'net USDT':>11}")
    for k, v in results.items():
        r = v["raw"]
        d = f"{r['per_year']/base_raw['per_year']*100-100:+.0f}%" if k != list(VARIANTS)[0] else "—"
        print(f"{k:<28}{r['per_year']:>12,.0f}{d:>10}{r['pf']:>8.3f}"
              f"{r['expectancy']:>+13.3f}{r['win_pct']:>8.1f}{r['net']:>+11,.0f}")

    print()
    print("=" * 96)
    print("  AS THE LIVE ACCOUNT WOULD TAKE THEM (20 slots + same-direction cap)")
    print("=" * 96)
    print(f"{'variant':<28}{'trades/yr':>12}{'vs live':>10}{'PF':>8}"
          f"{'expectancy':>13}{'win%':>8}{'net USDT':>11}")
    for k, v in results.items():
        r = v["live"]
        d = f"{r['per_year']/base_live['per_year']*100-100:+.0f}%" if k != list(VARIANTS)[0] else "—"
        print(f"{k:<28}{r['per_year']:>12,.0f}{d:>10}{r['pf']:>8.3f}"
              f"{r['expectancy']:>+13.3f}{r['win_pct']:>8.1f}{r['net']:>+11,.0f}")

    print()
    print("  Reading this: a filter EARNS its place if removing it adds trades while")
    print("  cutting PF and expectancy. It is REDUNDANT if removing it changes neither.")

    (ROOT / "research" / "results" / "filter_attribution.json").write_text(
        json.dumps({k: {kk: {m: round(x, 4) for m, x in vv.items()}
                        for kk, vv in v.items()} for k, v in results.items()},
                   indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
