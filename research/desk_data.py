"""Decision-desk data: 15m candles + order-flow context for the top-N USDT-M perps.

Source is Binance's public archive (data.binance.vision) - no key, no rate-limit
pressure on the account API. Per coin, three files land in data/market/desk/<SYM>/:

    klines_15m.parquet   OHLCV + taker_buy_volume  (-> trade-flow delta / CVD;
                         30m is resampled from this, never downloaded separately)
    metrics_5m.parquet   open interest, top-trader and global long/short ratios,
                         taker long/short volume ratio   (daily files, 5m steps)
    funding.parquet      funding rate history

Memory: this host has ~7.8 GB and Chrome usually holds a third of it, so the
script works ONE coin at a time and never holds more than that coin in RAM.
Resumable: a coin whose three files already exist is skipped (use --force).
Progress is written to data/market/desk/status.json for the UI to show.

    .venv\\Scripts\\python.exe research\\desk_data.py            # top 30, from 2024-09-01
    .venv\\Scripts\\python.exe research\\desk_data.py --top 5    # quick trial
"""
from __future__ import annotations

import argparse
import io
import json
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "market" / "desk"
ARCHIVE = "https://data.binance.vision/data/futures/um"
FAPI = "https://fapi.binance.com/fapi/v1"

# Stablecoin-vs-stablecoin and index-style contracts carry no directional signal.
EXCLUDE = {"USDCUSDT", "FDUSDUSDT", "BTCDOMUSDT", "DEFIUSDT", "USDPUSDT", "TUSDUSDT"}

KLINE_COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
              "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]

S = requests.Session()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_status(st: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    st["updated"] = now_utc()
    tmp = OUT / "status.json.tmp"
    tmp.write_text(json.dumps(st, indent=1), encoding="utf-8")
    tmp.replace(OUT / "status.json")


# ------------------------------------------------------------------ universe
def pick_universe(top: int, start: date) -> list[dict]:
    """Top-N by 24h quote volume among coin perps listed before `start`.

    Requiring a listing date before the window start keeps every coin on the
    same 2-year span; a coin listed mid-window would carry a different regime
    mix and quietly bias any cross-coin comparison.
    """
    info = S.get(f"{FAPI}/exchangeInfo", timeout=30).json()
    eligible = {}
    cutoff_ms = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp() * 1000)
    for s in info["symbols"]:
        if (s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT"
                and s.get("status") == "TRADING" and s.get("underlyingType", "COIN") == "COIN"
                and s["symbol"] not in EXCLUDE and int(s.get("onboardDate", 0)) <= cutoff_ms):
            eligible[s["symbol"]] = s
    tick = S.get(f"{FAPI}/ticker/24hr", timeout=30).json()
    ranked = sorted((t for t in tick if t["symbol"] in eligible),
                    key=lambda t: float(t["quoteVolume"]), reverse=True)[:top]
    return [{"symbol": t["symbol"], "quote_volume_24h": round(float(t["quoteVolume"])),
             "onboard": datetime.fromtimestamp(int(eligible[t["symbol"]]["onboardDate"]) / 1000,
                                               tz=timezone.utc).date().isoformat()}
            for t in ranked]


# ------------------------------------------------------------------ fetching
def fetch_zip_csv(url: str) -> pd.DataFrame | None:
    for attempt in range(4):
        try:
            r = S.get(url, timeout=60)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                with z.open(z.namelist()[0]) as f:
                    return pd.read_csv(f, header=None, dtype=str)
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed after retries: {url}")


def months(start: date, end: date):
    d = date(start.year, start.month, 1)
    while d <= end:
        yield d
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def days(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def _frame(raw: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    # Some archive files carry a header row, some do not.
    if str(raw.iat[0, 0]).strip() == cols[0]:
        raw = raw.iloc[1:]
    raw = raw.iloc[:, :len(cols)]
    raw.columns = cols
    return raw


def get_klines(sym: str, start: date, end: date, pool: ThreadPoolExecutor) -> pd.DataFrame:
    """Monthly files for complete months, daily files for the current month."""
    this_month = date(end.year, end.month, 1)
    urls = [f"{ARCHIVE}/monthly/klines/{sym}/15m/{sym}-15m-{m:%Y-%m}.zip"
            for m in months(start, end) if m < this_month]
    urls += [f"{ARCHIVE}/daily/klines/{sym}/15m/{sym}-15m-{d:%Y-%m-%d}.zip"
             for d in days(max(this_month, start), end)]
    parts = [p for p in pool.map(fetch_zip_csv, urls) if p is not None and len(p)]
    if not parts:
        return pd.DataFrame()
    df = pd.concat([_frame(p, KLINE_COLS) for p in parts], ignore_index=True)
    df = df.drop(columns=["ignore", "close_time"])
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["date"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.drop(columns=["open_time"]).drop_duplicates("date").sort_values("date")
    return df.reset_index(drop=True)


METRIC_COLS = ["create_time", "symbol", "sum_open_interest", "sum_open_interest_value",
               "count_toptrader_long_short_ratio", "sum_toptrader_long_short_ratio",
               "count_long_short_ratio", "sum_taker_long_short_vol_ratio"]


def get_metrics(sym: str, start: date, end: date, pool: ThreadPoolExecutor) -> tuple[pd.DataFrame, int]:
    urls = [f"{ARCHIVE}/daily/metrics/{sym}/{sym}-metrics-{d:%Y-%m-%d}.zip" for d in days(start, end)]
    res = list(pool.map(fetch_zip_csv, urls))
    missing = sum(1 for p in res if p is None)
    parts = [p for p in res if p is not None and len(p)]
    if not parts:
        return pd.DataFrame(), missing
    df = pd.concat([_frame(p, METRIC_COLS) for p in parts], ignore_index=True).drop(columns=["symbol"])
    df["date"] = pd.to_datetime(df.pop("create_time"), utc=True)
    for c in df.columns:
        if c != "date":
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.rename(columns={
        "sum_open_interest": "oi", "sum_open_interest_value": "oi_value",
        "count_toptrader_long_short_ratio": "top_ls_accounts",
        "sum_toptrader_long_short_ratio": "top_ls_positions",
        "count_long_short_ratio": "global_ls", "sum_taker_long_short_vol_ratio": "taker_ls"})
    return df.drop_duplicates("date").sort_values("date").reset_index(drop=True), missing


def get_funding(sym: str, start: date, end: date, pool: ThreadPoolExecutor) -> pd.DataFrame:
    this_month = date(end.year, end.month, 1)
    urls = [f"{ARCHIVE}/monthly/fundingRate/{sym}/{sym}-fundingRate-{m:%Y-%m}.zip"
            for m in months(start, end) if m < this_month]
    parts = [p for p in pool.map(fetch_zip_csv, urls) if p is not None and len(p)]
    df = (pd.concat([_frame(p, ["calc_time", "interval_hours", "rate"]) for p in parts], ignore_index=True)
          if parts else pd.DataFrame(columns=["calc_time", "interval_hours", "rate"]))
    # The archive stops at the last complete month; top up from the REST endpoint.
    try:
        since = int(datetime(this_month.year, this_month.month, 1, tzinfo=timezone.utc).timestamp() * 1000)
        rest = S.get(f"{FAPI}/fundingRate", params={"symbol": sym, "startTime": since, "limit": 1000},
                     timeout=30).json()
        if rest:
            df = pd.concat([df, pd.DataFrame({"calc_time": [r["fundingTime"] for r in rest],
                                              "interval_hours": None,
                                              "rate": [r["fundingRate"] for r in rest]})],
                           ignore_index=True)
    except Exception:
        pass
    df["date"] = pd.to_datetime(pd.to_numeric(df.pop("calc_time"), errors="coerce"), unit="ms", utc=True)
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
    df["interval_hours"] = pd.to_numeric(df["interval_hours"], errors="coerce")
    return df.dropna(subset=["date"]).drop_duplicates("date").sort_values("date").reset_index(drop=True)


# ------------------------------------------------------------------ main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--start", default="2024-09-01")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    start = date.fromisoformat(a.start)
    end = datetime.now(timezone.utc).date() - timedelta(days=1)   # yesterday is the last complete day
    uni = pick_universe(a.top, start)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "universe.json").write_text(json.dumps({
        "generated": now_utc(), "method": f"top {a.top} USDT-M coin perps by 24h quote volume, "
        f"listed on or before {start}, stable/index contracts excluded",
        "window": [start.isoformat(), end.isoformat()], "coins": uni}, indent=1), encoding="utf-8")

    st = {"state": "running", "started": now_utc(), "window": [start.isoformat(), end.isoformat()],
          "total": len(uni), "done": [], "current": None, "errors": {}}
    write_status(st)

    with ThreadPoolExecutor(a.threads) as pool:
        for c in uni:
            sym = c["symbol"]
            d = OUT / sym
            files = [d / "klines_15m.parquet", d / "metrics_5m.parquet", d / "funding.parquet"]
            if not a.force and all(f.exists() for f in files):
                st["done"].append({"symbol": sym, "skipped": True})
                write_status(st)
                continue
            st["current"] = sym
            write_status(st)
            t0 = time.time()
            try:
                d.mkdir(parents=True, exist_ok=True)
                k = get_klines(sym, start, end, pool)
                k.to_parquet(files[0], index=False)
                m, missing = get_metrics(sym, start, end, pool)
                m.to_parquet(files[1], index=False)
                f = get_funding(sym, start, end, pool)
                f.to_parquet(files[2], index=False)
                st["done"].append({"symbol": sym, "klines": len(k), "metrics": len(m),
                                   "metrics_days_missing": missing, "funding": len(f),
                                   "first": str(k["date"].iloc[0]) if len(k) else None,
                                   "last": str(k["date"].iloc[-1]) if len(k) else None,
                                   "seconds": round(time.time() - t0)})
                del k, m, f
            except Exception as e:
                st["errors"][sym] = f"{type(e).__name__}: {str(e)[:200]}"
            write_status(st)

    st["state"] = "finished" if not st["errors"] else "finished_with_errors"
    st["current"] = None
    st["finished"] = now_utc()
    write_status(st)
    print(json.dumps({"done": len(st["done"]), "errors": st["errors"]}, indent=1))


if __name__ == "__main__":
    main()
