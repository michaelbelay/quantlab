r"""Point-in-time liquidity rank: each day, every coin ranked by its average daily traded volume over the
previous 30 days (rank 1 = most traded), across ALL 413 coins. Known at the start of the day -> no lookahead.

    .venv\Scripts\python.exe -m quant.liquidity      # -> data/liq_rank.parquet
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from .panel import load
from .paths import DATA


def build() -> pd.DataFrame:
    a, b = load("dev"), load("oos")
    q = pd.DataFrame(np.concatenate([a.qvol, b.qvol], axis=1), index=a.index, columns=a.coins + b.coins)
    daily = q.resample("1D").sum(min_count=1)
    avg30 = daily.rolling(30, min_periods=20).mean().shift(1)          # yesterday and before only
    return avg30.rank(axis=1, ascending=False)


def rank_series(coin: str, dates: pd.Series, table: pd.DataFrame) -> np.ndarray:
    if coin not in table.columns:
        return np.full(len(dates), np.nan)
    day = dates.dt.floor("D")
    return table[coin].reindex(pd.DatetimeIndex(day)).to_numpy()


def main() -> int:
    t = build()
    t.to_parquet(DATA / "liq_rank.parquet")
    print(t.shape, "| top-5 on 2024-01-01:", t.loc["2024-01-01"].nsmallest(5).index.tolist())
    return 0


if __name__ == "__main__":
    sys.exit(main())
