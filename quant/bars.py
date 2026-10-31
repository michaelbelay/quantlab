r"""Per-coin intraday bars for Protocol C.

    bars("BTC", "1h")    -> 1h bars, any of the 413 coins (dev + unseen), 2021-01 .. 2026-09
    bars("ETH", "15m")   -> 15m bars, the 30 desk coins, 2024-09 .. 2026-09 (has taker_buy)
    bars("ETH", "30m")   -> resampled from 15m

Columns: date (bar open, UTC), open, high, low, close, qvol (USDT), taker_buy (base units, 15m/30m only,
else NaN), volume (base units), fund (summed funding rate of events in (open, close], longs pay +).
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

from .paths import DESK, FUT, OOS, dev_coins, oos_coins

TF = {"15m": pd.Timedelta(minutes=15), "30m": pd.Timedelta(minutes=30), "1h": pd.Timedelta(hours=1)}


@lru_cache(maxsize=1)
def universe_1h() -> tuple[str, ...]:
    return tuple(dev_coins() + oos_coins())


def universe_15m() -> tuple[str, ...]:
    return tuple(sorted(d.name[:-4] for d in DESK.iterdir() if d.is_dir() and (d / "klines_15m.parquet").exists()))


def _fund_into(dates: pd.Series, bar: pd.Timedelta, ev_t: pd.Series, ev_r: np.ndarray) -> np.ndarray:
    t0 = dates.iloc[0]
    k = np.ceil(((ev_t.dt.floor("min").dt.as_unit("ns") - t0) / bar).to_numpy(dtype=float)).astype(int) - 1
    ok = (k >= 0) & (k < len(dates))
    return np.bincount(k[ok], weights=ev_r[ok], minlength=len(dates))


def bars(coin: str, tf: str) -> pd.DataFrame:
    bar = TF[tf]
    if tf == "1h":
        if (FUT / f"{coin}_USDT_USDT-1h-futures.feather").exists():
            h = pd.read_feather(FUT / f"{coin}_USDT_USDT-1h-futures.feather")
            fp = FUT / f"{coin}_USDT_USDT-1h-funding_rate.feather"
        else:
            h = pd.read_feather(OOS / f"{coin}USDT" / "ohlcv_1h.feather")
            fp = OOS / f"{coin}USDT" / "funding.feather"
        h = h.drop_duplicates("date").sort_values("date").reset_index(drop=True)
        h["date"] = h["date"].dt.as_unit("ns")
        df = pd.DataFrame({"date": h["date"], "open": h["open"].astype(float), "high": h["high"].astype(float),
                           "low": h["low"].astype(float), "close": h["close"].astype(float),
                           "volume": h["volume"].astype(float)})
        df["qvol"] = df["close"] * df["volume"]
        df["taker_buy"] = np.nan
        f = pd.read_feather(fp) if fp.exists() else None
        ev_t, ev_r = (f["date"], f.iloc[:, 1].to_numpy(dtype=float)) if f is not None and len(f) else (None, None)
    else:
        k = pd.read_parquet(DESK / f"{coin}USDT" / "klines_15m.parquet",
                            columns=["date", "open", "high", "low", "close", "volume", "quote_volume", "taker_buy_volume"])
        k = k.drop_duplicates("date").sort_values("date")
        k["date"] = k["date"].dt.as_unit("ns")
        k = k.set_index("date")
        if tf == "30m":
            g = k.resample(bar, origin="epoch")
            k = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                              "close": g["close"].last(), "volume": g["volume"].sum(),
                              "quote_volume": g["quote_volume"].sum(), "taker_buy_volume": g["taker_buy_volume"].sum()}
                             ).dropna(subset=["close"])
        k = k.reset_index()
        df = pd.DataFrame({"date": k["date"], "open": k["open"], "high": k["high"], "low": k["low"], "close": k["close"],
                           "volume": k["volume"], "qvol": k["quote_volume"], "taker_buy": k["taker_buy_volume"]})
        f = pd.read_parquet(DESK / f"{coin}USDT" / "funding.parquet")
        ev_t, ev_r = f["date"], f["rate"].to_numpy(dtype=float)
    df["fund"] = _fund_into(df["date"], bar, ev_t, ev_r) if ev_t is not None else 0.0
    return df.reset_index(drop=True)
