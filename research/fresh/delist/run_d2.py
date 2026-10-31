"""Delisting-announcement short. Rule: ../REGISTER_DELIST_2026-10-25.md.

    .venv\\Scripts\\python.exe research\\fresh\\delist\\run.py
"""
from __future__ import annotations

import io
import json
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "candles_5m"
CACHE.mkdir(exist_ok=True)
STOP, HOLD, COST, NOTION = 0.15, 72 * 12, 0.003, 30.0   # D2: 5m bars
STABLE = {"SUSD", "TUSD", "USDP", "PAX", "BUSD", "USDC", "FDUSD", "DAI", "EUR", "GBP", "AUD", "UST", "USTC", "RENBTC", "WBTC"}
COLS = ["date", "open", "high", "low", "close", "volume"]


def fapi(sym: str, t0: int) -> pd.DataFrame | None:
    u = f"https://fapi.binance.com/fapi/v1/klines?symbol={sym}&interval=5m&startTime={t0}&limit=1000"
    try:
        raw = json.loads(urllib.request.urlopen(u, timeout=20).read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None
    if not raw:
        return None
    return pd.DataFrame([r[:6] for r in raw], columns=COLS)


def archive(sym: str, ts: pd.Timestamp) -> pd.DataFrame | None:
    parts = []
    for m in sorted({ts.strftime("%Y-%m"), (ts + pd.Timedelta(days=5)).strftime("%Y-%m")}):
        u = f"https://data.binance.vision/data/futures/um/monthly/klines/{sym}/5m/{sym}-5m-{m}.zip"
        try:
            z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(u, timeout=30).read()))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, zipfile.BadZipFile):
            continue
        df = pd.read_csv(z.open(z.namelist()[0]), header=None)
        if not str(df.iloc[0, 0]).isdigit():
            df = df.iloc[1:]
        parts.append(df.iloc[:, :6].set_axis(COLS, axis=1))
    return pd.concat(parts) if parts else None


def candles(coin: str, ts: pd.Timestamp) -> pd.DataFrame | None:
    f = CACHE / f"{coin}_{int(ts.timestamp())}.feather"
    if f.exists():
        return pd.read_feather(f)
    sym = coin + "USDT"
    t0 = int((ts - pd.Timedelta(minutes=10)).timestamp() * 1000)
    df = fapi(sym, t0)
    if df is None or len(df) < 5:
        df = archive(sym, ts)
    time.sleep(0.2)
    if df is None or not len(df):
        return None
    df["date"] = pd.to_datetime(df["date"].astype("int64"), unit="ms", utc=True)
    df[COLS[1:]] = df[COLS[1:]].astype(float)
    df = df.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    df.to_feather(f)
    return df


ev = json.load(open(HERE / "events.json"))
rows, missing = [], []
for coin, ms in ev.items():
    if coin in STABLE:
        continue
    ts = pd.Timestamp(ms, unit="ms", tz="UTC")
    df = candles(coin, ts)
    if df is None:
        missing.append(coin)
        continue
    after = df[df["date"] >= ts.ceil("5min")].reset_index(drop=True)          # first full candle starting after the news
    if len(after) < 2:
        missing.append(coin)
        continue
    e = after.loc[0, "close"]
    last = min(HOLD, len(after) - 1 - 36 if len(after) < HOLD + 37 else HOLD)
    if last < 1:
        missing.append(coin)
        continue
    res, j, why = None, last, "time"
    for k in range(1, last + 1):
        if after.loc[k, "high"] >= e * (1 + STOP):
            res, j, why = -STOP, k, "stop"
            break
    if res is None:
        res = -(after.loc[j, "close"] / e - 1)
    pre = df[df["date"] < ts.floor("5min")]
    jump = (e / pre["close"].iloc[-1] - 1) if len(pre) else None                 # move already gone before entry
    rows.append((coin, ts, after.loc[0, "date"], j, res - COST, (res - COST) * NOTION, why, jump))
T = pd.DataFrame(rows, columns=["coin", "news", "entry", "hours", "net", "usdt", "exit", "move_before_entry"])
T.to_csv(HERE / "trades_d2.csv", index=False)
yr = T.groupby(T["news"].dt.year)["net"].agg(["count", "mean", "sum"])
big = yr[yr["count"] >= 5]
wins = T[T.usdt > 0]
ok = len(T) >= 40 and T.net.mean() >= 0.02 and T.net.median() >= 0 and (big["mean"] > 0).sum() >= 3 and wins.usdt.mean() >= 1
out = {"events": len(ev), "traded": len(T), "no_candles": len(missing), "avg_net_pct": round(float(T.net.mean()) * 100, 2),
       "median_net_pct": round(float(T.net.median()) * 100, 2), "win_pct": round(float((T.net > 0).mean()) * 100, 1),
       "total_usdt_at_30": round(float(T.usdt.sum()), 1), "avg_win_usdt": round(float(wins.usdt.mean()), 2),
       "avg_loss_usdt": round(float(T.loc[T.usdt <= 0, "usdt"].mean()), 2), "worst_usdt": round(float(T.usdt.min()), 2),
       "stops": int((T.exit == "stop").sum()), "avg_hours": round(float(T.hours.mean()) / 12, 1),
       "avg_move_before_entry_pct": round(float(T.move_before_entry.mean()) * 100, 2),
       "years": {int(k): {"n": int(v["count"]), "avg_pct": round(float(v["mean"]) * 100, 2)} for k, v in yr.iterrows()},
       "verdict": "🟡 paper forward test" if ok else "🔴", "missing_sample": missing[:30]}
(HERE / "result_d2.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out))
