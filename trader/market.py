"""Binance USD-M public market data: hourly candles with taker-buy volume, and last prices."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import ccxt
import pandas as pd

from .flowtrend import HISTORY_H


def exchange(keys: dict | None = None) -> ccxt.binanceusdm:
    cfg = {"enableRateLimit": True, "options": {"defaultType": "future"}}
    if keys:
        cfg.update(apiKey=keys["key"], secret=keys["secret"])
    return ccxt.binanceusdm(cfg)


def symbol(coin: str) -> str:
    return f"{coin}/USDT:USDT"


def candles(ex: ccxt.binanceusdm, coin: str, now: pd.Timestamp) -> pd.DataFrame:
    """Last HISTORY_H CLOSED 1h candles. Columns open high low close volume qv tbq, index = candle open time (UTC)."""
    rows = ex.fapiPublicGetKlines({"symbol": f"{coin}USDT", "interval": "1h", "limit": HISTORY_H})
    d = pd.DataFrame({"date": pd.to_datetime([int(r[0]) for r in rows], unit="ms", utc=True),
                      "open": [float(r[1]) for r in rows], "high": [float(r[2]) for r in rows],
                      "low": [float(r[3]) for r in rows], "close": [float(r[4]) for r in rows],
                      "volume": [float(r[5]) for r in rows], "qv": [float(r[7]) for r in rows],
                      "tbq": [float(r[10]) for r in rows]}).set_index("date")
    return d[d.index + pd.Timedelta(hours=1) <= now]               # drop the candle still forming


def all_candles(ex: ccxt.binanceusdm, coins: list[str], now: pd.Timestamp) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Read every coin in parallel. Returns (frames, coins that failed). A failed coin simply has no signal."""
    def one(c):
        try:
            return c, candles(ex, c, now)
        except Exception:
            return c, None
    with ThreadPoolExecutor(max_workers=8) as pool:
        got = dict(pool.map(one, coins))
    return {c: d for c, d in got.items() if d is not None and len(d)}, [c for c, d in got.items() if d is None]


def last_prices(ex: ccxt.binanceusdm, coins: list[str]) -> dict[str, float]:
    if not coins:
        return {}
    t = ex.fetch_tickers([symbol(c) for c in coins])
    return {c: float(t[symbol(c)]["last"]) for c in coins if symbol(c) in t and t[symbol(c)].get("last")}
