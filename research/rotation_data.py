"""Point-in-time universe for the rotation test (PREREGISTRATION_2026-09-28_rotation.md §3).

Every USDT-margined perpetual in Binance's public archive, delisted ones included.
Public data only - no key, no account API. Per symbol, into data/market/rotation/<SYM>/:

    klines_1h.parquet   date, open, close, volume, quote_volume
    funding.parquet     date, rate           (may be empty; counted in the audit)

Resumable: a symbol whose klines file exists is skipped (use --force).

    .venv\\Scripts\\python.exe research\\rotation_data.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from desk_data import ARCHIVE, FAPI, KLINE_COLS, S, _frame, days, fetch_zip_csv  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "market" / "rotation"
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
START, END = date(2021, 1, 1), date(2026, 9, 25)
# §3 exclusions, fixed in the pre-registration
EXCLUDE = {"USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "USDPUSDT", "BUSDUSDT", "BTCDOMUSDT", "DEFIUSDT",
           "FOOTBALLUSDT", "BLUEBIRDUSDT"}
STABLE_BASES = {"USDC", "FDUSD", "TUSD", "USDP", "BUSD", "DAI", "USDE", "PYUSD", "USD1", "RLUSD", "USDS", "EUR"}


def s3_list(prefix: str, delimiter: str | None = "/") -> list[str]:
    """All keys (delimiter=None) or common prefixes (delimiter='/') under a prefix."""
    out, marker = [], ""
    while True:
        params = {"prefix": prefix, "marker": marker}
        if delimiter:
            params["delimiter"] = delimiter
        for attempt in range(4):
            try:
                r = S.get(S3, params=params, timeout=60).text
                break
            except Exception:
                time.sleep(2 * (attempt + 1))
        else:
            raise RuntimeError(f"s3 list failed: {prefix}")
        tag = "Prefix" if delimiter else "Key"
        got = re.findall(rf"<{tag}>([^<]+)</{tag}>", r)
        got = [g for g in got if g != prefix]
        out += got
        if "<IsTruncated>true</IsTruncated>" not in r or not got:
            return out
        marker = got[-1]


def symbols() -> list[str]:
    pre = "data/futures/um/monthly/klines/"
    syms = [p[len(pre):].strip("/") for p in s3_list(pre)]
    keep = []
    for s in syms:
        if not s.endswith("USDT") or "_" in s or s in EXCLUDE:
            continue
        if s[:-4] in STABLE_BASES:
            continue
        keep.append(s)
    return sorted(set(keep))


def get_symbol(sym: str, pool: ThreadPoolExecutor) -> dict:
    keys = s3_list(f"data/futures/um/monthly/klines/{sym}/1h/", delimiter=None)
    months = sorted(m.group(1) for m in (re.search(r"-1h-(\d{4}-\d{2})\.zip$", k) for k in keys) if m)
    months = [m for m in months if f"{START:%Y-%m}" <= m < f"{END:%Y-%m}"]
    urls = [f"{ARCHIVE}/monthly/klines/{sym}/1h/{sym}-1h-{m}.zip" for m in months]
    # the last month has no monthly file yet: daily files, only for symbols alive in the month before
    last_month = date(END.year, END.month, 1)
    prev = (last_month - timedelta(days=1)).strftime("%Y-%m")
    if any(k.endswith(f"-1h-{prev}.zip") for k in keys):
        urls += [f"{ARCHIVE}/daily/klines/{sym}/1h/{sym}-1h-{d:%Y-%m-%d}.zip" for d in days(last_month, END)]
    parts = [p for p in pool.map(fetch_zip_csv, urls) if p is not None and len(p)]
    if not parts:
        return {"klines": pd.DataFrame(), "funding": pd.DataFrame()}
    k = pd.concat([_frame(p, KLINE_COLS) for p in parts], ignore_index=True)
    k = k[["open_time", "open", "close", "volume", "quote_volume"]]
    for c in k.columns:
        k[c] = pd.to_numeric(k[c], errors="coerce")
    k["date"] = pd.to_datetime(k.pop("open_time"), unit="ms", utc=True)
    k = k[(k["date"] >= pd.Timestamp(START, tz="UTC")) &
          (k["date"] < pd.Timestamp(END, tz="UTC") + pd.Timedelta(days=1))]
    k = k.drop_duplicates("date").sort_values("date").reset_index(drop=True)

    fkeys = s3_list(f"data/futures/um/monthly/fundingRate/{sym}/", delimiter=None)
    fm = [m.group(1) for m in (re.search(r"-fundingRate-(\d{4}-\d{2})\.zip$", x) for x in fkeys) if m]
    furls = [f"{ARCHIVE}/monthly/fundingRate/{sym}/{sym}-fundingRate-{m}.zip" for m in sorted(fm)
             if f"{START:%Y-%m}" <= m < f"{END:%Y-%m}"]
    fparts = [p for p in pool.map(fetch_zip_csv, furls) if p is not None and len(p)]
    f = (pd.concat([_frame(p, ["calc_time", "interval_hours", "rate"]) for p in fparts], ignore_index=True)
         if fparts else pd.DataFrame(columns=["calc_time", "interval_hours", "rate"]))
    f = f[["calc_time", "rate"]]
    if len(k) and k["date"].iloc[-1] >= pd.Timestamp(last_month, tz="UTC"):
        try:
            since = int(datetime(last_month.year, last_month.month, 1, tzinfo=timezone.utc).timestamp() * 1000)
            rest = S.get(f"{FAPI}/fundingRate", params={"symbol": sym, "startTime": since, "limit": 1000},
                         timeout=30).json()
            if isinstance(rest, list) and rest:
                f = pd.concat([f, pd.DataFrame({"calc_time": [r["fundingTime"] for r in rest],
                                                "rate": [r["fundingRate"] for r in rest]})], ignore_index=True)
        except Exception:
            pass
    f["date"] = pd.to_datetime(pd.to_numeric(f.pop("calc_time"), errors="coerce"), unit="ms", utc=True)
    f["rate"] = pd.to_numeric(f["rate"], errors="coerce")
    f = f.dropna().drop_duplicates("date").sort_values("date")
    f = f[f["date"] < pd.Timestamp(END, tz="UTC") + pd.Timedelta(days=1)].reset_index(drop=True)
    return {"klines": k, "funding": f}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, default=16)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    syms = symbols()
    (OUT / "symbols.json").write_text(json.dumps({"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                                  "count": len(syms), "symbols": syms}, indent=1), encoding="utf-8")
    print(f"{len(syms)} USDT perpetuals after exclusions", flush=True)
    t0, errors = time.time(), {}
    with ThreadPoolExecutor(a.threads) as pool:
        for i, sym in enumerate(syms, 1):
            d = OUT / sym
            if (d / "klines_1h.parquet").exists() and not a.force:
                continue
            try:
                r = get_symbol(sym, pool)
                d.mkdir(parents=True, exist_ok=True)
                r["klines"].to_parquet(d / "klines_1h.parquet", index=False)
                r["funding"].to_parquet(d / "funding.parquet", index=False)
            except Exception as e:
                errors[sym] = f"{type(e).__name__}: {str(e)[:200]}"
            if i % 25 == 0:
                print(f"  {i}/{len(syms)}  {time.time() - t0:.0f}s  errors={len(errors)}", flush=True)
    (OUT / "download_errors.json").write_text(json.dumps(errors, indent=1), encoding="utf-8")
    print(f"done in {time.time() - t0:.0f}s, errors: {len(errors)}", flush=True)


if __name__ == "__main__":
    main()
