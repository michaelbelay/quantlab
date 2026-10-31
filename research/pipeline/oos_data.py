"""Out-of-sample universe for the research pipeline (gate G4), 2026-10-04.

RULE (fixed here, before any return is computed on these coins):
  * every USDT-margined perpetual in Binance's public archive, delisted ones included
    (the 859-symbol list in data/market/rotation);
  * minus the 140 coins the research engine has used (data/market/universe/split_140.json,
    dev AND legacy holdout - both are development data since 2026-10-04);
  * minus the 15 desk holdout coins sealed for the short-1h confirmation (pause note §1c);
  * minus stablecoin / index contracts;
  * minus non-crypto underlyings: Binance exchangeInfo underlyingType EQUITY / KR_EQUITY /
    COMMODITY ("TradFi" perpetuals on stocks, gold, oil...). Added 2026-10-04 before any return
    was computed; symbols no longer listed (delisted) are crypto by construction of the archive;

  * at least 2,160 hourly bars (90 days) and a median daily quote volume >= 5,000,000 USDT
    over the symbol's own life (liquidity only - no price or return is looked at).

Data: full 1h OHLCV from data.binance.vision (public archive, no key), written in the
engine's format to data/market/extra_coins_1h/<SYM>/{ohlcv_1h.feather, funding.feather}.
Funding is copied from data/market/rotation (already downloaded).

    .venv\\Scripts\\python.exe research\\pipeline\\oos_data.py --select     # write the universe only
    .venv\\Scripts\\python.exe research\\pipeline\\oos_data.py              # select (if needed) + download
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "research"))
from desk_data import ARCHIVE, KLINE_COLS, _frame, fetch_zip_csv  # noqa: E402
from rotation_data import END, START, STABLE_BASES, s3_list  # noqa: E402

ROT = ROOT / "data" / "market" / "rotation"
OUT = ROOT / "data" / "market" / "extra_coins_1h"
UNIVERSE = HERE / "oos_universe.json"
DESK_SEALED = ["ETH", "SOL", "ENA", "SUI", "RARE", "TAO", "FIL", "LTC", "1000PEPE", "QNT", "DASH", "ARK",
               "AAVE", "SAGA", "FET"]
MIN_BARS = 2160
MIN_MEDIAN_DAILY_QV = 5_000_000


def select() -> dict:
    split = json.loads((ROOT / "data" / "market" / "universe" / "split_140.json").read_text(encoding="utf-8"))
    used = {c.upper() for c in split["dev"] + split["holdout"]} | set(DESK_SEALED)
    import requests
    info = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo", timeout=30).json()
    utype = {s["symbol"]: s.get("underlyingType") for s in info["symbols"]}
    (HERE / "exchangeinfo_underlying_2026-10-04.json").write_text(json.dumps(utype, indent=0), encoding="utf-8")
    rows, kept = [], []
    for d in sorted(p for p in ROT.iterdir() if p.is_dir()):
        sym = d.name
        base = sym[:-4]
        why = None
        if base in used:
            why = "used by the research engine (split_140) or sealed (desk)"
        elif base in STABLE_BASES:
            why = "stablecoin"
        elif utype.get(sym) not in (None, "COIN"):
            why = f"non-crypto underlying ({utype[sym]})"
        else:
            kp = d / "klines_1h.parquet"
            if not kp.exists():
                why = "no data"
            else:
                k = pd.read_parquet(kp)
                if not {"date", "quote_volume"} <= set(k.columns):
                    why = "empty data file"
                elif len(k) < MIN_BARS:
                    why = f"{len(k)} bars < {MIN_BARS}"
                else:
                    med = float(k.set_index("date")["quote_volume"].resample("1D").sum().median())
                    if med < MIN_MEDIAN_DAILY_QV:
                        why = f"median daily volume {med:,.0f} < {MIN_MEDIAN_DAILY_QV:,}"
        rows.append({"symbol": sym, "kept": why is None, "why": why})
        if why is None:
            kept.append(sym)
    doc = {"created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "rule": __doc__.split("RULE")[1].split("Data:")[0].strip(),
           "period": [str(START), str(END)], "kept": kept, "n_kept": len(kept), "n_considered": len(rows),
           "excluded": [r for r in rows if not r["kept"]]}
    UNIVERSE.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    return doc


def get(sym: str, pool: ThreadPoolExecutor) -> str:
    out = OUT / sym
    if (out / "ohlcv_1h.feather").exists():
        return "cached"
    keys = s3_list(f"data/futures/um/monthly/klines/{sym}/1h/", delimiter=None)
    months = sorted(m.group(1) for m in (re.search(r"-1h-(\d{4}-\d{2})\.zip$", k) for k in keys) if m)
    months = [m for m in months if f"{START:%Y-%m}" <= m < f"{END:%Y-%m}"]
    parts = [p for p in pool.map(fetch_zip_csv, [f"{ARCHIVE}/monthly/klines/{sym}/1h/{sym}-1h-{m}.zip" for m in months])
             if p is not None and len(p)]
    if not parts:
        return "no data"
    k = pd.concat([_frame(p, KLINE_COLS) for p in parts], ignore_index=True)[["open_time", "open", "high", "low", "close", "volume"]]
    for c in k.columns:
        k[c] = pd.to_numeric(k[c], errors="coerce")
    k["date"] = pd.to_datetime(k.pop("open_time"), unit="ms", utc=True)
    k = k.dropna().drop_duplicates("date").sort_values("date").reset_index(drop=True)[["date", "open", "high", "low", "close", "volume"]]
    out.mkdir(parents=True, exist_ok=True)
    fp = ROT / sym / "funding.parquet"
    if fp.exists():
        f = pd.read_parquet(fp).rename(columns={"rate": "funding_rate"})[["date", "funding_rate"]]
        f["date"] = f["date"].dt.floor("h")
        f.drop_duplicates("date").reset_index(drop=True).to_feather(out / "funding.feather")
    k.to_feather(out / "ohlcv_1h.feather")
    return f"{len(k)} bars"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--select", action="store_true", help="write the universe file and stop")
    ap.add_argument("--threads", type=int, default=8)
    a = ap.parse_args()
    doc = json.loads(UNIVERSE.read_text(encoding="utf-8")) if UNIVERSE.exists() else select()
    print(f"OOS universe: {doc['n_kept']} of {doc['n_considered']} symbols (rule fixed {doc['created']})", flush=True)
    if a.select:
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(a.threads) as pool:
        for i, sym in enumerate(doc["kept"], 1):
            try:
                r = get(sym, pool)
            except Exception as e:
                r = f"FAILED {type(e).__name__}: {e}"
            print(f"[{i}/{doc['n_kept']}] {sym}: {r}", flush=True)
    print("OOS_DATA_COMPLETE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
