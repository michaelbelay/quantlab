"""Download Binance SPOT 1h klines with taker-buy volume (data.binance.vision, public) for the coins that were
point-in-time top-10 (batch B universe). Saves data/market/flow/<COIN>.feather. 2026-10-13."""
import io, sys, zipfile, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "market" / "flow_spot"
coins = sys.argv[1].split(",")
months = pd.period_range("2021-01", "2026-09", freq="M")
def get(sym, m):
    u = f"https://data.binance.vision/data/spot/monthly/klines/{sym}/1h/{sym}-1h-{m}.zip"
    try:
        b = urllib.request.urlopen(u, timeout=60).read()
    except Exception:
        return None
    z = zipfile.ZipFile(io.BytesIO(b))
    raw = z.read(z.namelist()[0])
    df = pd.read_csv(io.BytesIO(raw), header=None if not raw[:9].startswith(b"open_time") else 0)
    df = df.iloc[:, [0, 5, 7, 9, 10]]
    df.columns = ["t", "volume", "quote_volume", "taker_buy_volume", "taker_buy_quote"]
    return df
for c in coins:
    f = OUT / f"{c}.feather"
    if f.exists():
        continue
    sym = f"{c}USDT"
    with ThreadPoolExecutor(8) as ex:
        parts = [p for p in ex.map(lambda m: get(sym, m), months) if p is not None]
    if not parts:
        print(c, "none"); continue
    d = pd.concat(parts)
    t = d.t.astype("int64")
    t = t.where(t < 10**14, t // 1000)                     # spot archives use microseconds from 2025
    d["date"] = pd.to_datetime(t, unit="ms", utc=True)
    d.drop(columns="t").reset_index(drop=True).to_feather(f)
    print(c, len(d), flush=True)
