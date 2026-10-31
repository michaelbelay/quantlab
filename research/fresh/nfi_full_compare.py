"""NFI X8: full non-meme list (220 coins) vs the 48-coin list, 2024-04..2026-09 (REGISTER_NFI_FULL_2026-10-21.md).

Compounded wallets are not realistic at these sizes (unlimited fills), so the comparison is on trade frequency,
quiet stretches, per-trade results and a fixed-stake book: every trade 50 USDT (300 / 6 slots), nothing reinvested.

    .venv\\Scripts\\python.exe research\\fresh\\nfi_full_compare.py
"""
import sys

import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from nfi_bt_summary import trades  # noqa: E402

STAKE = 50.0


def stats(lst: str) -> dict:
    t = trades(lst).sort_values("open")
    o = t.open
    g = o.diff().dt.total_seconds().dropna() / 86400
    span = (o.iloc[-1] - o.iloc[0]).total_seconds() / 86400
    pnl = (t.sort_values("close").set_index("close").profit_ratio * STAKE)
    book = 300 + pnl.cumsum()
    dd = ((book - book.cummax()) / book.cummax()).min() * 100
    month = pnl.groupby(pnl.index.strftime("%Y-%m")).sum()
    liq = t.exit_reason.str.contains("liquidat", case=False).sum()
    day = o.dt.date.value_counts()
    return {
        "coins traded": t.pair.nunique(),
        "trades": len(t),
        "trades / week": round(len(t) / span * 7, 1),
        "days with an entry": f"{o.dt.date.nunique()} of {span:.0f}",
        "median gap (days)": round(g.median(), 2),
        "p90 gap (days)": round(g.quantile(0.9), 1),
        "longest gap (days)": round(g.max(), 1),
        "time in quiet stretches >= 4.5 d": f"{g[g >= 4.5].sum() / span * 100:.0f}%",
        "share of trades on the 5% busiest days": f"{day[day >= day.quantile(0.95)].sum() / len(t) * 100:.0f}%",
        "win rate": f"{(t.profit_abs > 0).mean() * 100:.1f}%",
        "avg trade": f"{t.profit_ratio.mean() * 100:+.2f}%",
        "worst trade": f"{t.profit_ratio.min() * 100:+.1f}%",
        "liquidations": int(liq),
        "longs / shorts": f"{(~t.is_short).sum()} / {t.is_short.sum()}",
        "fixed-stake book 300 ->": round(book.iloc[-1]),
        "fixed-stake worst drop": f"{dd:.1f}%",
        "months positive (fixed)": f"{(month > 0).sum()}/{len(month)}",
        "worst month (fixed, USDT)": round(month.min(), 1),
    }


def main() -> None:
    df = pd.DataFrame({"48 coins": stats("nfi48"), "220 coins (full list)": stats("full223")})
    print(df.to_string())


if __name__ == "__main__":
    main()
