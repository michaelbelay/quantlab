"""How often does the LIVE spec actually trade? Measured, not estimated.

The premise behind this whole investigation was "~100 trades/year". Before
loosening a single filter it is worth knowing whether that is true, because
every filter we relax to chase frequency costs something, and relaxing them to
fix a problem that does not exist would be pure damage.

Three numbers matter and they are not the same:

  AGGREGATE     every signal the strategy produces, no capital constraint.
                This is what `universe_run.py` reports and it overstates what a
                real account can take.
  SLOT-CAPPED   what a book of N slots can actually hold. Signals arriving on a
                full book are REFUSED - that refusal rate is the gap between the
                research number and the live number.
  PER PAIR      how long any individual coin waits between signals.

Also reported: the clustering that makes an average misleading (trades arrive in
bursts around volatility), and the longest stretch with no trade at all - the
number that actually determines whether the system feels "too sparse".

    python research/frequency_baseline.py                 # live universe, 20 slots
    python research/frequency_baseline.py --slots 10
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "engine"))
from backtest import Config, simulate_pair   # noqa: E402
from features import load_pair               # noqa: E402

# The live spec, exactly as VBreak4Both/VBreak4Live implements it.
LIVE_SPEC = {"family": "volatility_breakout", "direction": "both",
             "filters": ["btc_regime", "volume"], "trend_mode": "with",
             "params": {"bars": 4, "atr_mult": 2.0}}
LIVE_CFG = dict(leverage=1.0, stop_mode="atr", stop_atr=2.0, tp_mode="none",
                tp_atr=(), tp_frac=(), entry_mode="instant")


def live_universe() -> list[str]:
    """The pairs the live bot can actually trade: whitelist minus blacklist."""
    cfg = json.loads((ROOT / "configs" / "live_coins_2026-10.json").read_text(encoding="utf-8"))
    return [p.split("/")[0] for p in cfg["pair_whitelist"]]


def load(coins: list[str]):
    uni, missing = {}, []
    for c in coins:
        f = load_pair(c, futures=True)
        if f is None or len(f.close) < 400:
            missing.append(c)
            continue
        uni[c] = f
    return uni, missing


def slot_cap(trades: list[dict], slots: int) -> tuple[list[dict], int]:
    """Replay chronologically; refuse anything arriving on a full book.

    This is what makes the research number and the live number differ, and it is
    the honest way to answer 'how many trades will I actually see'.
    """
    taken, refused, book = [], 0, []   # book holds exit timestamps
    for t in sorted(trades, key=lambda x: x["entry"]):
        book = [x for x in book if x > t["entry"]]
        if len(book) >= slots:
            refused += 1
            continue
        taken.append(t)
        book.append(t["exit"])
    return taken, refused


def gaps(dates: pd.Series) -> dict:
    d = dates.sort_values().reset_index(drop=True)
    g = d.diff().dropna()
    if g.empty:
        return {}
    longest = g.max()
    return {
        "longest_gap_days": round(longest.total_seconds() / 86400, 1),
        "longest_gap_start": str(d[g.idxmax() - 1].date()),
        "median_gap_hours": round(g.median().total_seconds() / 3600, 1),
        "p90_gap_days": round(g.quantile(0.90).total_seconds() / 86400, 2),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slots", type=int, default=20)
    a = ap.parse_args()

    coins = live_universe()
    print(f"live universe: {len(coins)} tradeable pairs", flush=True)
    uni, missing = load(coins)
    print(f"with usable history: {len(uni)}   no data: {len(missing)}"
          + (f"  {' '.join(missing[:12])}" if missing else ""), flush=True)

    cfg = Config(**LIVE_CFG)
    rows = []
    for pair, f in uni.items():
        for t in simulate_pair(f, LIVE_SPEC, cfg, pair):
            rows.append({"pair": pair, "side": "long" if t.side > 0 else "short",
                         "pnl": t.pnl, "bars": t.bars, "reason": t.reason,
                         "entry": pd.Timestamp(f.date[t.entry_i]),
                         "exit": pd.Timestamp(f.date[t.exit_i])})
    df = pd.DataFrame(rows)
    df["entry"] = pd.to_datetime(df.entry, utc=True)
    df["exit"] = pd.to_datetime(df.exit, utc=True)
    span = (df.entry.max() - df.entry.min())
    yrs = span.days / 365.25

    print()
    print("=" * 74)
    print(f"  BASELINE - the live spec on the live universe, {df.entry.min().date()} to {df.entry.max().date()}")
    print("=" * 74)

    agg = len(df) / yrs
    print(f"\nAGGREGATE (no capital constraint - what the research reports)")
    print(f"  {len(df):,} trades over {yrs:.2f} years")
    print(f"  {agg:,.0f} trades/year      {agg/52:.1f} per week      {agg/365.25:.2f} per day")

    taken, refused = slot_cap(df.to_dict("records"), a.slots)
    tdf = pd.DataFrame(taken)
    ly = len(tdf) / yrs
    print(f"\nSLOT-CAPPED at {a.slots} slots (what the live account will see)")
    print(f"  {len(tdf):,} taken, {refused:,} refused on a full book "
          f"({refused/len(df)*100:.1f}% refusal)")
    print(f"  {ly:,.0f} trades/year      {ly/52:.1f} per week      {ly/365.25:.2f} per day")

    print(f"\nPER PAIR")
    per = df.groupby("pair").size()
    print(f"  {per.mean()/yrs:.1f} trades/year on the average pair "
          f"(median {per.median()/yrs:.1f}, range {per.min()/yrs:.1f}-{per.max()/yrs:.1f})")
    print(f"  busiest : {', '.join(f'{p} {n/yrs:.0f}' for p, n in per.nlargest(6).items())}")
    print(f"  quietest: {', '.join(f'{p} {n/yrs:.1f}' for p, n in per.nsmallest(6).items())}")

    print(f"\nCLUSTERING AND DROUGHTS (slot-capped stream)")
    g = gaps(tdf.entry)
    print(f"  longest stretch with NO trade: {g['longest_gap_days']} days (from {g['longest_gap_start']})")
    print(f"  median gap between trades    : {g['median_gap_hours']} hours")
    print(f"  90th percentile gap          : {g['p90_gap_days']} days")
    wk = tdf.set_index("entry").resample("W").size()
    print(f"  weeks with zero trades       : {(wk == 0).sum()} of {len(wk)} ({(wk==0).mean()*100:.1f}%)")
    print(f"  busiest week                 : {wk.max()} trades")
    print(f"  weekly distribution          : p10={wk.quantile(.1):.0f} median={wk.median():.0f} p90={wk.quantile(.9):.0f}")

    print(f"\nECONOMICS (aggregate, 1000 USDT reference wallet)")
    w = df[df.pnl > 0].pnl.sum(); l = -df[df.pnl < 0].pnl.sum()
    print(f"  profit factor {w/l:.3f}   expectancy {df.pnl.mean():+.3f} USDT/trade   "
          f"win rate {(df.pnl>0).mean()*100:.1f}%")
    print(f"  long {(df.side=='long').sum():,} trades {df[df.side=='long'].pnl.sum():+,.0f}   "
          f"short {(df.side=='short').sum():,} trades {df[df.side=='short'].pnl.sum():+,.0f}")
    print(f"  median hold {df.bars.median():.0f}h   exit reasons: "
          + ", ".join(f"{k} {v}" for k, v in df.reason.value_counts().head(5).items()))

    out = ROOT / "research" / "results" / "frequency_baseline.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "pairs": len(uni), "years": round(yrs, 2),
        "aggregate_trades": len(df), "aggregate_per_year": round(agg),
        "slots": a.slots, "capped_trades": len(tdf), "capped_per_year": round(ly),
        "refusal_pct": round(refused / len(df) * 100, 1),
        "per_pair_per_year": round(per.mean() / yrs, 2),
        **g,
        "profit_factor": round(w / l, 3), "expectancy": round(df.pnl.mean(), 4),
    }, indent=2) + "\n", encoding="utf-8")
    print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
