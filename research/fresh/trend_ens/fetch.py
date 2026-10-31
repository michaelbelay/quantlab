"""Daily USDT-M futures candles (public Binance API, no key) for the NFIFull 220 + BTC/ETH, from 2020-01-01. 2026-10-25."""
import json, time, urllib.request
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
PAIRS = json.loads((HERE.parent / "strat_bt" / "CrashShort" / "config.json").read_text())["exchange"]["pair_whitelist"]
syms = sorted({p.split("/")[0] + "USDT" for p in PAIRS} | {"BTCUSDT", "ETHUSDT"})
URL = "https://fapi.binance.com/fapi/v1/klines?symbol={s}&interval=1d&limit=1500&startTime={t}"
for s in syms:
    rows, t = [], int(pd.Timestamp("2020-01-01", tz="UTC").timestamp() * 1000)
    try:
        while True:
            raw = json.loads(urllib.request.urlopen(URL.format(s=s, t=t), timeout=30).read())
            rows += raw
            if len(raw) < 1500: break
            t = raw[-1][0] + 1
            time.sleep(0.2)
    except Exception as e:
        print(s, "fail", type(e).__name__); continue
    df = pd.DataFrame([r[:8] for r in rows], columns=["date","open","high","low","close","volume","ct","qv"]).drop(columns="ct")
    df["date"] = pd.to_datetime(df["date"], unit="ms", utc=True)
    df[df.columns[1:]] = df[df.columns[1:]].astype(float)
    df = df[df["date"] < pd.Timestamp.now(tz="UTC").normalize()]          # closed days only
    df.reset_index(drop=True).to_feather(HERE / "data" / f"{s}.feather")
    time.sleep(0.15)
print("DONE", len(syms))
