"""1-minute candles for the desk universe - needed to simulate limit-order fills honestly.

Same source and same 30 coins as desk_data.py (read from the existing
data/market/desk/universe.json - the universe is NOT re-picked), same fixed
window as the 15m data (2024-09-01 .. 2026-09-25) so the sealed quadrant stays
identical. Writes data/market/desk/<SYM>/klines_1m.parquet. One coin at a
time; resumable (existing files are skipped unless --force).

    .venv\\Scripts\\python.exe research\\desk_data_1m.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from desk_data import ARCHIVE, KLINE_COLS, OUT, _frame, days, fetch_zip_csv, months  # noqa: E402

START, END = date(2024, 9, 1), date(2026, 9, 25)


def get_1m(sym: str, pool: ThreadPoolExecutor) -> pd.DataFrame:
    # The archive has no monthly file for a month that is still running, so the
    # last month comes from daily files (first run silently stopped at 08-31).
    last_month = date(END.year, END.month, 1)
    urls = [f"{ARCHIVE}/monthly/klines/{sym}/1m/{sym}-1m-{m:%Y-%m}.zip"
            for m in months(START, END) if m < last_month]
    urls += [f"{ARCHIVE}/daily/klines/{sym}/1m/{sym}-1m-{d:%Y-%m-%d}.zip" for d in days(last_month, END)]
    parts = [p for p in pool.map(fetch_zip_csv, urls) if p is not None and len(p)]
    df = pd.concat([_frame(p, KLINE_COLS) for p in parts], ignore_index=True)
    df = df[["open_time", "open", "high", "low", "close", "volume"]]
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["date"] = pd.to_datetime(df.pop("open_time"), unit="ms", utc=True)
    df = df[(df["date"] >= pd.Timestamp(START, tz="UTC")) & (df["date"] < pd.Timestamp(END, tz="UTC") + pd.Timedelta(days=1))]
    df = df.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    if df["date"].iloc[-1] < pd.Timestamp(END, tz="UTC") + pd.Timedelta(hours=23, minutes=59):
        raise RuntimeError(f"incomplete: last candle {df['date'].iloc[-1]}")
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    coins = [c["symbol"] for c in json.loads((OUT / "universe.json").read_text(encoding="utf-8"))["coins"]]
    t_all = time.time()
    with ThreadPoolExecutor(a.threads) as pool:
        for i, sym in enumerate(coins, 1):
            f = OUT / sym / "klines_1m.parquet"
            if f.exists() and not a.force:
                print(f"[{i}/{len(coins)}] {sym} skipped (exists)", flush=True)
                continue
            t0 = time.time()
            try:
                df = get_1m(sym, pool)
                df.to_parquet(f, index=False)
                print(f"[{i}/{len(coins)}] {sym} {len(df)} rows {df['date'].iloc[0]} .. {df['date'].iloc[-1]}"
                      f" ({time.time() - t0:.0f}s)", flush=True)
                del df
            except Exception as e:
                print(f"[{i}/{len(coins)}] {sym} ERROR {type(e).__name__}: {str(e)[:200]}", flush=True)
    print(f"done in {time.time() - t_all:.0f}s", flush=True)


if __name__ == "__main__":
    main()
