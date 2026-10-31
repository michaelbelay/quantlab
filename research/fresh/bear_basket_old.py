"""Bear batch idea 10 / 10b (weekly basket) on the untouched years 2022-02 .. 2024-03, same rule (2026-10-24).

    .venv\\Scripts\\python.exe research\\fresh\\bear_basket_old.py

Same coins (NFIFull 220, only those with data then), same code as bear_batch.basket; nothing changed but the period.
"""
from __future__ import annotations

import json

import pandas as pd

import bear_batch as bb

bb.START, bb.END, bb.MID = (pd.Timestamp("2022-02-07", tz="UTC"), pd.Timestamp("2024-04-01", tz="UTC"), pd.Timestamp("2023-03-01", tz="UTC"))
btc = pd.read_feather(bb.DATA / "BTC_USDT_USDT-1h-futures.feather").set_index("date").sort_index()
bear = (btc["close"] < btc["close"].rolling(1200).mean()).shift(1)
closes = {}
for p in bb.PAIRS:
    f = bb.DATA / f"{p.split('/')[0]}_USDT_USDT-1h-futures.feather"
    if f.exists():
        s = pd.read_feather(f).set_index("date").sort_index()["close"]
        closes[p] = s[s.index < bb.END + pd.Timedelta(days=8)]
C = pd.DataFrame(closes)
r = bb.basket(C, bear)
cov = C[(C.index >= bb.START) & (C.index < bb.END)].notna().any().sum()
print(json.dumps({"coins_with_data": int(cov), "halves": "A 2022-02..2023-02, B 2023-03..2024-03", **r}, indent=1))
print("DONE")
