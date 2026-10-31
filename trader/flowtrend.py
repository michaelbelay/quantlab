"""FlowTrend signal - quantlab's own implementation.

Rule (1h candles, Binance USD-M perpetuals):
  buy share  = taker-buy quote volume / quote volume over the last 24h
  z          = (buy share - its 720h mean) / its 720h sd      (needs >= 500h of history)
  LONG       10-day return > 0 and z >= +2
  SHORT      10-day return < 0 and z <= -2
  only coins in the month's top 10 by the PREVIOUS calendar month's traded value (close x volume, >= 20 days of data)
  one signal per coin and side per 24h (counted only for signals that pass the top-10 filter)
  stop       2 x the coin's daily move (sd of 1h log returns over 720h x sqrt 24) from entry
  exit       48h after entry
"""
from __future__ import annotations

import numpy as np
import pandas as pd

Z_MIN = 2.0
TREND_H = 240
WIN_H = 24
NORM_H = 720
NORM_MIN = 500
HOLD_H = 48
STOP_K = 2.0
COOLDOWN_H = 24
TOP_N = 10
HISTORY_H = 1500          # hours of candles needed for one decision


def indicators(d: pd.DataFrame) -> pd.DataFrame:
    """d: index = candle open time (UTC, hourly), columns close, volume, qv (quote volume), tbq (taker-buy quote)."""
    d = d.copy()
    lc = np.log(d["close"])
    d["sig24"] = lc.diff().rolling(NORM_H, min_periods=NORM_MIN).std() * np.sqrt(24)
    d["r10"] = lc - lc.shift(TREND_H)
    qv, tbq = d["qv"].fillna(0.0), d["tbq"].fillna(0.0)
    share = tbq.rolling(WIN_H).sum() / qv.rolling(WIN_H).sum().replace(0, np.nan)
    d["z"] = (share - share.rolling(NORM_H, min_periods=NORM_MIN).mean()) / share.rolling(NORM_H, min_periods=NORM_MIN).std()
    ok = d["sig24"].notna() & (d["sig24"] > 0) & (d["volume"] > 0)
    d["raw_long"] = ok & (d["r10"] > 0) & (d["z"] >= Z_MIN)
    d["raw_short"] = ok & (d["r10"] < 0) & (d["z"] <= -Z_MIN)
    return d


def month_of(t: pd.Timestamp) -> pd.Timestamp:
    return t.tz_convert("UTC").replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def top_coins(frames: dict[str, pd.DataFrame], month: pd.Timestamp) -> set[str] | None:
    """Top-N coins for `month` by the previous calendar month's close x volume. None if too few coins have data."""
    prev0 = month_of(month - pd.Timedelta(days=1))
    val = {}
    for c, d in frames.items():
        w = d[(d.index >= prev0) & (d.index < month)]
        if len(w) >= 24 * 20:
            val[c] = float((w["close"] * w["volume"]).sum())
    if len(val) < TOP_N:
        return None
    return set(sorted(val, key=val.get, reverse=True)[:TOP_N])


def signals(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """All signals over the frames' history. frames: coin -> indicators() output.
    Returns rows: time (signal candle open), coin, short, sig24, close (signal candle close = entry reference)."""
    months: dict[pd.Timestamp, set[str] | None] = {}
    rows = []
    for c, d in frames.items():
        for side, col in ((False, "raw_long"), (True, "raw_short")):
            last = None
            for t in d.index[d[col].to_numpy()]:
                m = month_of(t)
                if m not in months:
                    months[m] = top_coins(frames, m)
                top = months[m]
                if top is None or c not in top:
                    continue
                if last is not None and t - last < pd.Timedelta(hours=COOLDOWN_H):
                    continue
                last = t
                rows.append({"time": t, "coin": c, "short": side, "sig24": float(d.at[t, "sig24"]),
                             "close": float(d.at[t, "close"])})
    out = pd.DataFrame(rows, columns=["time", "coin", "short", "sig24", "close"])
    return out.sort_values(["time", "coin"]).reset_index(drop=True)


def stop_price(entry: float, sig24: float, short: bool) -> float:
    k = STOP_K * sig24
    return entry * (1 + k) if short else entry * (1 - k)
