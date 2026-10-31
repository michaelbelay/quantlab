r"""Summary of the outside-strategy backtests (quant/run_ext.py) -> runs/EXT_BACKTEST_2026-10-12.json + printed table.

    .venv\Scripts\python.exe -m quant.ext_report

Per month (each chunk starts from 300 USDT): trades, net USDT, PF, worst drop inside the month. Chained: the monthly
returns compounded (what 300 USDT would have become if each month's % had been earned in a row). Robustness views:
without trades opened on 2025-10-10 (flash crash: 5m-candle fills at the wick bottom are not realistic) and without
the 3 best days.
"""
from __future__ import annotations

import json
import zipfile

import pandas as pd

from .paths import DATA, RUNS

RES = DATA / "ext" / "results"
CRASH = pd.Timestamp("2025-10-10").date()


def load(pid: str) -> pd.DataFrame:
    by_start = {}
    for z in sorted(RES.joinpath(pid).glob("*.zip")):                       # names sort by time: latest wins
        zf = zipfile.ZipFile(z)
        name = next(n for n in zf.namelist() if n.endswith(".json") and "_config" not in n and "meta" not in n)
        s = next(iter(json.loads(zf.read(name))["strategy"].values()))
        start, end = s["backtest_start"][:10], s["backtest_end"][:10]
        if (pd.Timestamp(end) - pd.Timestamp(start)).days < 10 and end != "2026-10-12":   # the one-week memory trial
            continue
        t = pd.DataFrame(s["trades"])
        t["month"] = start
        by_start[start] = t
    t = pd.concat(by_start.values(), ignore_index=True)
    t["open_date"] = pd.to_datetime(t["open_date"], utc=True)
    t["close_date"] = pd.to_datetime(t["close_date"], utc=True)
    return t


def pf(x: pd.Series) -> float | None:
    loss = -x[x < 0].sum()
    return round(float(x[x > 0].sum() / loss), 2) if loss > 0 else None


def month_dd(t: pd.DataFrame) -> float:
    eq = 300 + t.sort_values("close_date")["profit_abs"].cumsum()
    eq = pd.concat([pd.Series([300.0]), eq])
    return round(float((1 - eq / eq.cummax()).max() * 100), 1)


def summary(t: pd.DataFrame) -> dict:
    months = {}
    for m, g in t.groupby("month"):
        months[m] = {"trades": int(len(g)), "net": round(float(g.profit_abs.sum()), 1), "pf": pf(g.profit_abs),
                     "dd_closed_pct": month_dd(g), "losers": int((g.profit_abs < 0).sum())}
    chained = 300.0
    for v in months.values():
        chained *= 1 + v["net"] / 300
    day = t.groupby(t.close_date.dt.date)["profit_abs"].sum()
    return {"trades": int(len(t)), "net_sum": round(float(t.profit_abs.sum()), 1), "pf": pf(t.profit_abs),
            "losing_months": sum(v["net"] < 0 for v in months.values()), "months": months,
            "chained_300": round(chained, 1),
            "best_day": [str(day.idxmax()), round(float(day.max()), 1)],
            "best3_days_share": round(float(day.nlargest(3).sum() / day.sum()), 2) if day.sum() > 0 else None}


def main() -> None:
    out = {}
    for pid in ("nfi-x8", "e0v1en"):
        t = load(pid)
        s = summary(t)
        s["without_2025_10_10"] = summary(t[t.open_date.dt.date != CRASH])
        top3 = t.groupby(t.close_date.dt.date)["profit_abs"].sum().nlargest(3).index
        s["without_best_3_days"] = summary(t[~t.close_date.dt.date.isin(top3)])
        out[pid] = s
        print(f"\n== {pid}: {s['trades']} trades, net {s['net_sum']}, PF {s['pf']}, chained 300 -> {s['chained_300']}, "
              f"losing months {s['losing_months']}/{len(s['months'])}, best day {s['best_day']}, best-3-day share {s['best3_days_share']}")
        for k in ("without_2025_10_10", "without_best_3_days"):
            v = s[k]
            print(f"   {k}: net {v['net_sum']}, PF {v['pf']}, chained {v['chained_300']}, losing months {v['losing_months']}")
        for m, v in s["months"].items():
            print(f"   {m}  trades {v['trades']:4d}  net {v['net']:8.1f}  PF {v['pf']}  dd {v['dd_closed_pct']}%  losers {v['losers']}")
    (RUNS / "EXT_BACKTEST_2026-10-12.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
