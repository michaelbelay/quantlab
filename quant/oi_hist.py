r"""Market-wide open interest, 1h, from Binance's public archive (daily `metrics` files, 5m OI).

    .venv\Scripts\python.exe -m quant.oi_hist download      # resumable, data/oi_hist/<SYM>.parquet (2021-01 .. 2024-08)
    .venv\Scripts\python.exe -m quant.oi_hist build         # -> data/mkt_oi_1h.parquet

Basket = the 30 desk coins (data/market/desk). From 2024-09 the existing desk 5m metrics are used.
Per symbol the hourly value is the last 5m OI value (USDT) inside the bar, i.e. known at the bar close.
Market 1h change at bar t = sum(OI_t) / sum(OI_{t-1}) - 1 over symbols present in BOTH bars (a listing cannot
create a jump). No symbol present in both bars -> missing.
"""
from __future__ import annotations

import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import numpy as np
import pandas as pd
import requests

from .paths import DATA, DESK, RESEARCH

sys.path.insert(0, str(RESEARCH))
from desk_data import get_metrics  # noqa: E402

OUT = DATA / "oi_hist"
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
START, END = date(2021, 1, 1), date(2024, 8, 31)


def basket() -> list[str]:
    return sorted(d.name for d in DESK.iterdir() if d.is_dir() and (d / "metrics_5m.parquet").exists())


def first_day(sym: str) -> date | None:
    r = requests.get(S3, params={"prefix": f"data/futures/um/daily/metrics/{sym}/", "max-keys": 2}, timeout=60).text
    m = re.search(r"-metrics-(\d{4}-\d{2}-\d{2})\.zip", r)
    return date.fromisoformat(m.group(1)) if m else None


def hourly(m: pd.DataFrame) -> pd.Series:
    s = m.set_index("date")["oi_value"]
    s = s[s > 0]
    return s.resample("1h", label="left", closed="left").last()


def download(budget: float = 540) -> bool:
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with ThreadPoolExecutor(16) as pool:
        for sym in basket():
            f = OUT / f"{sym}.parquet"
            if f.exists():
                continue
            fd = first_day(sym)
            if fd is None or fd > END:
                pd.Series(dtype=float, name="oi_value").to_frame().to_parquet(f)
                continue
            m, missing = get_metrics(sym, max(fd, START), END, pool)
            h = hourly(m) if len(m) else pd.Series(dtype=float)
            h.rename("oi_value").to_frame().to_parquet(f)
            print(f"  {sym}: from {max(fd, START)}  {len(h)} hours  ({missing} days missing)", flush=True)
            if time.time() - t0 > budget:
                return False
    return True


def build() -> pd.DataFrame:
    cols = {}
    for sym in basket():
        a = pd.read_parquet(OUT / f"{sym}.parquet")["oi_value"] if (OUT / f"{sym}.parquet").exists() else pd.Series(dtype=float)
        m = pd.read_parquet(DESK / sym / "metrics_5m.parquet", columns=["date", "oi_value"])
        m["date"] = m["date"].dt.as_unit("ns")
        b = hourly(m)
        a.index = pd.DatetimeIndex(a.index).as_unit("ns") if len(a) else a.index
        s = pd.concat([a[a.index < pd.Timestamp("2024-09-01", tz="UTC")] if len(a) else a, b]).sort_index()
        cols[sym] = s[~s.index.duplicated(keep="last")]
    oi = pd.DataFrame(cols)
    prev = oi.shift(1)
    both = oi.notna() & prev.notna()
    num, den = oi.where(both).sum(axis=1), prev.where(both).sum(axis=1)
    chg = (num / den - 1).where(both.any(axis=1))
    out = pd.DataFrame({"mkt_oi_chg_1h": chg, "coins": both.sum(axis=1)})
    out.to_parquet(DATA / "mkt_oi_1h.parquet")
    return out


def main() -> int:
    if sys.argv[1] == "download":
        return 0 if download() else 3
    out = build()
    ok = out["mkt_oi_chg_1h"].notna()
    print(f"hours with market OI change: {ok.sum()} of {len(out)}; first {out.index[ok][0]}, last {out.index[ok][-1]}")
    print("coins in basket by year:", out.groupby(out.index.year)["coins"].median().to_dict())
    print("hours with drop > 3%:", int((out['mkt_oi_chg_1h'] < -0.03).sum()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
