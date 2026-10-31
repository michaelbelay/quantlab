"""Batch L data: Binance USD-M aggTrades (data.binance.vision) -> 1-second last-trade prices, one .npy per coin/day.

    .venv\\Scripts\\python.exe research\\fresh\\get_ticks.py
"""
import io
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "market" / "ticks"
COINS = ["BTC", "ETH", "SOL", "XRP", "DOGE", "BNB"]
DAYS = pd.date_range("2026-07-23", "2026-09-20", freq="D")


def one(c, d):
    f = OUT / c / f"{d:%Y-%m-%d}.npy"
    if f.exists():
        return "skip"
    url = (f"https://data.binance.vision/data/futures/um/daily/aggTrades/{c}USDT/"
           f"{c}USDT-aggTrades-{d:%Y-%m-%d}.zip")
    raw = urllib.request.urlopen(url, timeout=120).read()
    z = zipfile.ZipFile(io.BytesIO(raw))
    with z.open(z.namelist()[0]) as fh:
        head = fh.read(64)
    with z.open(z.namelist()[0]) as fh:
        hdr = 0 if head[:1].isalpha() else None
        t = pd.read_csv(fh, header=hdr, usecols=[1, 5], names=None if hdr == 0 else range(7))
    t.columns = ["price", "time"]
    ms = t["time"].to_numpy()
    if ms.max() > 1e14:                                     # microseconds
        ms = ms // 1000
    sec = (ms - int(d.timestamp() * 1000)) // 1000
    ok = (sec >= 0) & (sec < 86400)
    s = pd.Series(t["price"].to_numpy()[ok], index=sec[ok]).groupby(level=0).last()
    p = s.reindex(range(86400)).ffill().bfill().to_numpy(np.float64)
    f.parent.mkdir(parents=True, exist_ok=True)
    np.save(f, p)
    return "ok"


if __name__ == "__main__":
    jobs = [(c, d) for c in COINS for d in DAYS]
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(lambda a: (a, one(*a)), jobs))
    print(f"{sum(r == 'ok' for _, r in res)} downloaded, {sum(r == 'skip' for _, r in res)} already there, "
          f"{len(jobs)} total")
