r"""C49 Meme crowd impulse, 1h (FAMILIES_C.md "C49", registered 2026-10-20 before this file existed).

    .venv\Scripts\python.exe -m quant.run_c49 dev
    .venv\Scripts\python.exe -m quant.run_c49 valid    # refused without a recorded DEV pass

The C48 rule on 1h bars built from the cached C48 15m klines: 24-bar baseline, trail 3 ATR14(1h), fade from the 4th
bar, time exit after 72 bars. Everything else (coins, costs, gates, twins) is C48's code unchanged.
"""
from __future__ import annotations

import sys

import pandas as pd

from . import run_c48 as m
from .paths import RUNS

_fetch15 = m.fetch


def fetch_1h(coin: str):
    d, fu = _fetch15(coin)
    if not len(d):
        return d, fu
    g = d.set_index("date").reindex(pd.date_range(d["date"].iloc[0].floor("h"), d["date"].iloc[-1], freq="15min"))
    r = g.resample("1h")
    out = pd.DataFrame({"open": r["open"].first(), "high": r["high"].max(), "low": r["low"].min(),
                        "close": r["close"].last(), "qvol": r["qvol"].sum(min_count=4), "count": r["count"].sum(min_count=4)})
    full = r["close"].count() == 4                     # an hour with any 15m bar missing = missing
    out = out[full].rename_axis("date").reset_index()
    return out, fu


m.fetch = fetch_1h
m.FAM, m.BPD, m.BAR_MIN, m.TF = "C49", 24, 60, "1h"
m.BASE, m.HOLD = 24, 72
m.OUT = RUNS / "c_trades" / "C49" / "1h"

if __name__ == "__main__":
    sys.exit(m.main())
