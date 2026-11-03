"""Open interest collector for the trader's coins (Binance USDT-M futures, public data, no key).

    .venv\\Scripts\\python.exe research\\oi\\oi_collector.py update          # fill every missing day, then the last ~41h
    .venv\\Scripts\\python.exe research\\oi\\oi_collector.py status          # coverage per coin

Sources:
- data.binance.vision daily "metrics" files (5m): open interest (coins and USDT), top-trader and all-account
  long/short ratios, taker buy/sell volume ratio. History from 2022-01-01; the archive is about 1 day behind.
- fapi /futures/data/openInterestHist (5m, last 500 rows ~41h) for the newest hours not yet in the archive
  (open interest only; source = "api"). Archive rows replace api rows once they exist.

Output: data/market/oi/<COIN>.parquet, index time (UTC, start of the 5m bar as in the file's create_time),
columns oi, oi_usdt, top_ls_accounts, top_ls_positions, ls_accounts, taker_ls_vol, source.
Run daily by the scheduled task "Quantlab OI Collector" (research\\oi\\oi_daily.bat).
"""
from __future__ import annotations

import io
import json
import sys
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from trader.settings import COINS  # noqa: E402

OUT = ROOT / "data" / "market" / "oi"
ARCHIVE = "https://data.binance.vision/data/futures/um/daily/metrics/{s}/{s}-metrics-{d}.zip"
API = "https://fapi.binance.com/futures/data/openInterestHist?symbol={s}&period=5m&limit=500"
START = pd.Timestamp("2022-01-01")
COLS = {"sum_open_interest": "oi", "sum_open_interest_value": "oi_usdt",
        "count_toptrader_long_short_ratio": "top_ls_accounts", "sum_toptrader_long_short_ratio": "top_ls_positions",
        "count_long_short_ratio": "ls_accounts", "sum_taker_long_short_vol_ratio": "taker_ls_vol"}


def symbol(c: str) -> str:
    return f"{c}USDT"


def get(url: str, tries: int = 3) -> bytes | None:
    for k in range(tries):
        try:
            return urllib.request.urlopen(url, timeout=60).read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:
            pass
        time.sleep(2 * (k + 1))
    return None


def archive_day(c: str, d: pd.Timestamp) -> pd.DataFrame | None:
    raw = get(ARCHIVE.format(s=symbol(c), d=f"{d:%Y-%m-%d}"))
    if raw is None:
        return None
    z = zipfile.ZipFile(io.BytesIO(raw))
    t = pd.read_csv(z.open(z.namelist()[0]))
    t["time"] = pd.to_datetime(t["create_time"], utc=True)
    t = t.rename(columns=COLS).set_index("time")[list(COLS.values())].apply(pd.to_numeric, errors="coerce")
    t["source"] = "archive"
    return t


def api_recent(c: str) -> pd.DataFrame | None:
    raw = get(API.format(s=symbol(c)))
    if raw is None:
        return None
    rows = json.loads(raw)
    if not isinstance(rows, list) or not rows:
        return None
    t = pd.DataFrame(rows)
    t["time"] = pd.to_datetime(t["timestamp"], unit="ms", utc=True)
    t = t.set_index("time").rename(columns={"sumOpenInterest": "oi", "sumOpenInterestValue": "oi_usdt"})[["oi", "oi_usdt"]]
    t = t.astype(float)
    t["source"] = "api"
    return t


def load(c: str) -> pd.DataFrame:
    p = OUT / f"{c}.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


def update_coin(c: str) -> str:
    cur = load(c)
    have = set() if cur.empty else set(cur[cur.source == "archive"].index.normalize().tz_localize(None))
    first = min(have) if have else START                                  # days before listing are not asked again
    days = [d for d in pd.date_range(first, pd.Timestamp.now("UTC").tz_localize(None).normalize() - pd.Timedelta(days=1))
            if d not in have]
    with ThreadPoolExecutor(8) as ex:
        parts = [p for p in ex.map(lambda d: archive_day(c, d), days) if p is not None]
    recent = api_recent(c)
    frames = [f for f in (cur, *parts) if not f.empty]
    df = pd.concat(frames) if frames else pd.DataFrame()
    if recent is not None:
        df = pd.concat([df, recent])
    if df.empty:
        return f"{c}: no data"
    df["rank"] = (df.source == "archive").astype(int)                     # archive wins over api for the same bar
    df = df.sort_values("rank").loc[lambda x: ~x.index.duplicated(keep="last")].drop(columns="rank").sort_index()
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / f"{c}.parquet.tmp"
    df.to_parquet(tmp)
    tmp.replace(OUT / f"{c}.parquet")   # atomic: readers never see a half-written file
    return f"{c}: +{len(parts)} archive days, rows {len(df)}, {df.index.min():%Y-%m-%d} -> {df.index.max():%Y-%m-%d %H:%M}"


def status():
    for c in COINS:
        df = load(c)
        if df.empty:
            print(f"{c:9s} none")
            continue
        days = df.index.normalize().nunique()
        span = (df.index.max().normalize() - df.index.min().normalize()).days + 1
        print(f"{c:9s} {df.index.min():%Y-%m-%d} -> {df.index.max():%Y-%m-%d %H:%M}  days {days}/{span}  rows {len(df)}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "update"
    if cmd == "status":
        return status()
    print(f"==== {pd.Timestamp.now("UTC"):%Y-%m-%d %H:%M} UTC update")
    for c in COINS:
        print(update_coin(c), flush=True)


if __name__ == "__main__":
    main()
