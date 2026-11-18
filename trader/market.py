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
        miss = [c for c, d in got.items() if d is None]
        if miss:                                    # one more try: a missing big coin would change the top-10 list
            got.update(pool.map(one, miss))
    return {c: d for c, d in got.items() if d is not None and len(d)}, [c for c, d in got.items() if d is None]


def last_prices(ex: ccxt.binanceusdm, coins: list[str]) -> dict[str, float]:
    if not coins:
        return {}
    t = ex.fetch_tickers([symbol(c) for c in coins])
    return {c: float(t[symbol(c)]["last"]) for c in coins if symbol(c) in t and t[symbol(c)].get("last")}


def hourly(ex: ccxt.binanceusdm, coin: str, start: pd.Timestamp, interval: str = "1h", limit: int = 1500) -> pd.DataFrame:
    """Candles from `start` on (the forming one included). Columns open high low close, index = candle open time (UTC)."""
    rows = ex.fapiPublicGetKlines({"symbol": f"{coin}USDT", "interval": interval, "limit": limit,
                                   "startTime": int(start.timestamp() * 1000)})
    return pd.DataFrame({"open": [float(r[1]) for r in rows], "high": [float(r[2]) for r in rows],
                         "low": [float(r[3]) for r in rows], "close": [float(r[4]) for r in rows]},
                        index=pd.to_datetime([int(r[0]) for r in rows], unit="ms", utc=True))


def funding_paid(ex: ccxt.binanceusdm, coin: str, short: bool, amount: float, start: pd.Timestamp, end: pd.Timestamp,
                 ref_price: float) -> float:
    """USDT of funding a position paid (+) or received (-) between two times: every funding stamp inside the
    holding time, rate x mark price x amount. Longs pay positive rates, shorts receive them."""
    rows = ex.fapiPublicGetFundingRate({"symbol": f"{coin}USDT", "startTime": int(start.timestamp() * 1000),
                                        "endTime": int(end.timestamp() * 1000), "limit": 1000})
    paid = 0.0
    for r in rows:
        if not int(start.timestamp() * 1000) < int(r["fundingTime"]) <= int(end.timestamp() * 1000):
            continue
        mark = float(r.get("markPrice") or 0) or ref_price
        paid += float(r["fundingRate"]) * mark * amount
    return -paid if short else paid
