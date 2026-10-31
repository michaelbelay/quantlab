"""Batch S data: 5m klines + 5m open interest (data.binance.vision) for point-in-time top-10 coins, 2021-12..2026-09.

    .venv\\Scripts\\python.exe research\\fresh\\get_oi.py
Output data/market/open_interest/<COIN>.feather: date, open, high, low, close, oi
"""
import io
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FUT = ROOT / "data" / "market" / "dev_1h" / "binance" / "futures"
OUT = ROOT / "data" / "market" / "open_interest"
OUT.mkdir(parents=True, exist_ok=True)
STABLE = {"USDC", "FDUSD", "TUSD", "BUSD", "USDP", "DAI", "EUR", "BTCDOM", "DEFI"}
BASE = "https://data.binance.vision/data/futures/um"

val = {}
for p in FUT.glob("*_USDT_USDT-1h-futures.feather"):
    n = p.name.split("_")[0]
    if n in STABLE:
        continue
    x = pd.read_feather(p, columns=["date", "close", "volume"])
    x["date"] = pd.to_datetime(x["date"], utc=True)
    val[n] = (x.set_index("date")["close"] * x.set_index("date")["volume"]).resample("MS").sum()
V = pd.DataFrame(val)
TOP = {m: set(V.shift(1).loc[m].dropna().nlargest(10).index) for m in V.index[1:]}
months = {}
for m, s in TOP.items():
    if pd.Timestamp("2022-01-01", tz="UTC") <= m <= pd.Timestamp("2026-09-01", tz="UTC"):
        for n in s:
            months.setdefault(n, set()).update({m, m - pd.offsets.MonthBegin(1)})


def get(url):
    try:
        raw = urllib.request.urlopen(url, timeout=60).read()
    except Exception:
        return None
    z = zipfile.ZipFile(io.BytesIO(raw))
    with z.open(z.namelist()[0]) as fh:
        return fh.read()


def kl(n, m):
    b = get(f"{BASE}/monthly/klines/{n}USDT/5m/{n}USDT-5m-{m:%Y-%m}.zip")
    if b is None:
        return None
    t = pd.read_csv(io.BytesIO(b), header=None, usecols=[0, 1, 2, 3, 4], names=["ts", "open", "high", "low", "close"])
    t = t[pd.to_numeric(t["ts"], errors="coerce").notna()].astype(float)
    t["date"] = pd.to_datetime(t["ts"].astype("int64"), unit="ms", utc=True)
    return t.drop(columns="ts")


def oi(n, d):
    b = get(f"{BASE}/daily/metrics/{n}USDT/{n}USDT-metrics-{d:%Y-%m-%d}.zip")
    if b is None:
        return None
    t = pd.read_csv(io.BytesIO(b), usecols=["create_time", "sum_open_interest"])
    t["date"] = pd.to_datetime(t["create_time"], utc=True)
    return t[["date", "sum_open_interest"]]


def coin(n):
    f = OUT / f"{n}.feather"
    if f.exists():
        return n, "skip"
    ms = sorted(months[n])
    with ThreadPoolExecutor(8) as ex:
        k = [x for x in ex.map(lambda m: kl(n, m), ms) if x is not None]
        days = [d for m in ms for d in pd.date_range(m, m + pd.offsets.MonthEnd(0), freq="D")]
        o = [x for x in ex.map(lambda d: oi(n, d), days) if x is not None]
    if not k or not o:
        return n, "no data"
    k = pd.concat(k).drop_duplicates("date").set_index("date").sort_index()
    o = pd.concat(o).drop_duplicates("date").set_index("date").sort_index()["sum_open_interest"]
    k["oi"] = o.reindex(k.index)
    k.reset_index().to_feather(f)
    return n, f"{len(k)} bars, oi {k['oi'].notna().mean()*100:.0f}%"


if __name__ == "__main__":
    for n in sorted(months):
        print(*coin(n), flush=True)
