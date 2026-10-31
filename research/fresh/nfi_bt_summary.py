"""Summary of the NFI X8 backtests (nfi_bt_chain.py): per list, trades, win rate, long/short, worst trades, and how far
each trade went against it while open (from the trade's own min/max price, at its leverage, as % of the money in it).

    .venv\\Scripts\\python.exe research\\fresh\\nfi_bt_summary.py
"""
import json
import zipfile
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent


def trades(lst: str) -> pd.DataFrame:
    rows = []
    for z in sorted((HERE / f"nfi_bt_{lst}").glob("bt_*-*.zip")):
        with zipfile.ZipFile(z) as f:
            name = next(n for n in f.namelist() if n.endswith(".json") and "_config" not in n and "meta" not in n)
            rows += json.loads(f.read(name))["strategy"]["NostalgiaForInfinityX8"]["trades"]
    t = pd.DataFrame(rows)
    t["open"] = pd.to_datetime(t["open_date"], utc=True)
    t["close"] = pd.to_datetime(t["close_date"], utc=True)
    # worst move against the trade while open, on the margin (leverage applied), vs the average entry price
    adverse = (t["min_rate"] / t["open_rate"] - 1).where(~t["is_short"], 1 - t["max_rate"] / t["open_rate"])
    t["worst_open_pct"] = adverse * t["leverage"] * 100
    return t


def main() -> None:
    for lst in ("nfi48", "ours20", "full223"):
        if not (HERE / f"nfi_bt_{lst}" / "chain_1m.json").exists():
            continue
        t = trades(lst)
        chain = json.loads((HERE / f"nfi_bt_{lst}" / "chain_1m.json").read_text(encoding="utf-8"))
        m = pd.DataFrame([{"month": r["tag"][:7], "pct": (r["end_wallet"] / r["start_wallet"] - 1) * 100} for r in chain])
        print(f"\n===== {lst}: {len(t)} trades, 300 -> {chain[-1]['end_wallet']:.0f}")
        print(f"win rate {(t.profit_abs > 0).mean() * 100:.1f}%  |  avg trade {t.profit_ratio.mean() * 100:+.2f}%  |  "
              f"median {t.profit_ratio.median() * 100:+.2f}%  |  longs {(~t.is_short).sum()} shorts {t.is_short.sum()}")
        o = t.open.sort_values()
        g = o.diff().dt.total_seconds().dropna() / 86400
        span = (o.iloc[-1] - o.iloc[0]).total_seconds() / 86400
        print(f"coins traded {t.pair.nunique()}  |  {len(t) / span * 7:.1f} trades/week  |  days with an entry "
              f"{o.dt.date.nunique()} of {span:.0f}  |  gap median {g.median():.2f} d, p90 {g.quantile(0.9):.1f} d, "
              f"max {g.max():.1f} d  |  time in dry spells >= 4.5 d {g[g >= 4.5].sum() / span * 100:.0f}%")
        print(f"avg hold {(t.close - t.open).mean()}  |  longest {(t.close - t.open).max()}")
        print(f"months positive {(m.pct > 0).sum()}/{len(m)}  |  median month {m.pct.median():+.1f}%  |  "
              f"worst month {m.pct.min():+.1f}% ({m.loc[m.pct.idxmin(), 'month']})")
        y = m.assign(y=m.month.str[:4]).groupby("y").pct.apply(lambda s: ((1 + s / 100).prod() - 1) * 100)
        print("by year:", "  ".join(f"{k} {v:+.0f}%" for k, v in y.items()))
        print("exit reasons:", t.exit_reason.str.split(" ").str[0].value_counts().head(6).to_dict())
        print("losing trades:", (t.profit_abs <= 0).sum(), "| worst 5 closed trades (% on money in the trade):")
        for _, r in t.nsmallest(5, "profit_ratio").iterrows():
            print(f"   {r.pair:16s} {'short' if r.is_short else 'long ':5s} {r.open:%Y-%m-%d} -> {r.close:%Y-%m-%d} "
                  f"{r.profit_ratio * 100:+.1f}%  ({r.exit_reason})")
        w = t.worst_open_pct
        print(f"how far trades went against them while open: median {w.median():.1f}%, "
              f"10% of trades worse than {w.quantile(0.1):.1f}%, worst {w.min():.1f}%")
        for _, r in t.nsmallest(5, "worst_open_pct").iterrows():
            print(f"   {r.pair:16s} {'short' if r.is_short else 'long ':5s} {r.open:%Y-%m-%d} dipped {r.worst_open_pct:.1f}%"
                  f" -> closed {r.profit_ratio * 100:+.1f}% after {r.close - r.open}, {r.get('nr_of_successful_entries', '?')} buys")


if __name__ == "__main__":
    main()
