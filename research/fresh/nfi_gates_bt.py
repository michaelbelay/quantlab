"""NFI coin-level gates on the 30-month NFI backtest trades (2026-10-22). Rule: REGISTER_NFI_GATES_2026-10-22.md.

    .venv\\Scripts\\python.exe research\\fresh\\nfi_gates_bt.py      # downloads (cached), features, report

Output: research/fresh/nfi_gates/trades.csv (one row per trade with its features and gate flags), report.json.
"""
from __future__ import annotations

import io
import json
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / "nfi_gates"
CACHE = OUT / "metrics"
DATA = ROOT / "data" / "market" / "main" / "binance" / "futures"
STAKE = 200 / 6
URL = "https://data.binance.vision/data/futures/um/daily/metrics/{s}/{s}-metrics-{d}.zip"
COLS = {"sum_open_interest_value": "oi", "count_long_short_ratio": "ls", "count_toptrader_long_short_ratio": "top",
        "sum_taker_long_short_vol_ratio": "taker"}


def fetch(sym: str, day: str) -> None:
    f = CACHE / f"{sym}-{day}.csv"
    if f.exists() or (CACHE / f"{sym}-{day}.none").exists():
        return
    for attempt in range(4):
        try:
            raw = urllib.request.urlopen(URL.format(s=sym, d=day), timeout=30).read()
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                f.write_bytes(z.read(z.namelist()[0]))
            return
        except urllib.error.HTTPError as e:
            if e.code == 404:
                (CACHE / f"{sym}-{day}.none").touch()
                return
        except Exception:  # noqa: BLE001 - network hiccup, retry with backoff
            pass
        time.sleep(2 ** attempt)


def metrics(sym: str, days: list[str]) -> pd.DataFrame:
    parts = [pd.read_csv(CACHE / f"{sym}-{d}.csv") for d in days if (CACHE / f"{sym}-{d}.csv").exists()]
    if not parts:
        return pd.DataFrame()
    m = pd.concat(parts)
    m["t"] = pd.to_datetime(m["create_time"], utc=True)
    return m.rename(columns=COLS).set_index("t").sort_index()[list(COLS.values())]


def candles(coin: str, kind: str) -> pd.DataFrame:
    df = pd.read_feather(DATA / f"{coin}_USDT_USDT-1h-{kind}.feather")
    return df.set_index("date").sort_index()


def features(t: dict, c1h: pd.DataFrame, fund: pd.DataFrame) -> dict:
    t0 = pd.Timestamp(t["open_date"])
    sym = t["pair"].split("/")[0] + "USDT"
    r: dict = {}
    # 1h candles that CLOSED before entry: candle start <= t0 - 1h
    h = c1h[c1h.index <= t0 - pd.Timedelta(hours=1)]
    last24, prev = h[h.index > t0 - pd.Timedelta(hours=25)], h[h.index <= t0 - pd.Timedelta(hours=25)]
    if len(last24) >= 20 and len(prev) >= 24:
        base = prev["close"].iloc[-1]
        qv = h["volume"] * h["close"]
        med = qv[(qv.index <= t0 - pd.Timedelta(hours=25)) & (qv.index > t0 - pd.Timedelta(days=7))].median()
        r["pump24"] = last24["high"].max() / base - 1
        r["volspike24"] = (qv.loc[last24.index].max() / med) if med and med > 0 else np.nan
        r["price_chg4"] = h["close"].iloc[-1] / h["close"].iloc[-5] - 1
    f = fund[fund.index <= t0]
    if len(f) >= 30:
        hist = f["funding_rate"].iloc[-91:-1]
        sd = hist.std()
        r["funding"] = f["funding_rate"].iloc[-1]
        r["funding_z"] = (r["funding"] - hist.mean()) / sd if sd and sd > 0 else 0.0
    days = sorted({(t0 - pd.Timedelta(days=1)).strftime("%Y-%m-%d"), t0.strftime("%Y-%m-%d")})
    m = metrics(sym, days)
    if len(m):
        m = m[m.index <= t0 - pd.Timedelta(minutes=5)]
        oi = m["oi"].dropna()
        ago24 = oi[oi.index <= t0 - pd.Timedelta(hours=24)]
        ago4 = oi[oi.index <= t0 - pd.Timedelta(hours=4)]
        if len(ago24) and len(oi):
            win = oi[oi.index > ago24.index[-1]]
            r["oi_rise24"] = win.max() / ago24.iloc[-1] - 1 if len(win) else np.nan
        if len(ago4) and len(oi):
            r["oi_chg4"] = oi.iloc[-1] / ago4.iloc[-1] - 1
        r["taker_1h"] = m["taker"].iloc[-12:].mean() if len(m) else np.nan
        r["ls"] = m["ls"].iloc[-1] if len(m) else np.nan
        r["top"] = m["top"].iloc[-1] if len(m) else np.nan
    return r


def gates(df: pd.DataFrame) -> pd.DataFrame:
    L, S = ~df["is_short"], df["is_short"]
    g = lambda c: df.get(c, pd.Series(np.nan, index=df.index))  # noqa: E731
    df["G1_pumpdump"] = L & (g("pump24") >= 0.15) & (g("volspike24") >= 10)
    df["G2_oispike"] = L & (g("oi_rise24") >= 0.30)
    df["G3_crowded_long"] = L & (g("funding_z") >= 2) & (g("oi_chg4") >= 0.05) & (g("price_chg4").abs() <= 0.02)
    df["G4_crowded_short"] = S & (g("funding_z") <= -2) & (g("oi_chg4") >= 0.05) & (g("price_chg4") >= -0.02)
    return df


def summary(d: pd.DataFrame) -> dict:
    if not len(d):
        return {"trades": 0}
    return {"trades": int(len(d)), "win_rate": round(float((d["usdt"] > 0).mean() * 100), 1),
            "avg_pct": round(float(d["profit_ratio"].mean() * 100), 2), "usdt": round(float(d["usdt"].sum()), 2),
            "worst_pct": round(float(d["profit_ratio"].min() * 100), 1)}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    CACHE.mkdir(exist_ok=True)
    T = pd.DataFrame([t for r in json.loads((HERE / "nfi_bt_full223" / "chain_1m.json").read_text()) for t in r["trades"]])
    T["open_date"] = pd.to_datetime(T["open_date"], utc=True)
    need = set()
    for p, t0 in zip(T["pair"], T["open_date"]):
        s = p.split("/")[0] + "USDT"
        need |= {(s, (t0 - pd.Timedelta(days=1)).strftime("%Y-%m-%d")), (s, t0.strftime("%Y-%m-%d"))}
    print(f"{len(T)} trades, {len(need)} metrics files to fetch (cached ones skipped)", flush=True)
    with ThreadPoolExecutor(8) as ex:
        for i, _ in enumerate(ex.map(lambda a: fetch(*a), sorted(need))):
            if i % 500 == 0:
                print(f"  fetched {i}/{len(need)}", flush=True)
    rows = []
    for coin, grp in T.groupby(T["pair"].str.split("/").str[0]):
        try:
            c1h, fund = candles(coin, "futures"), candles(coin, "funding_rate")
        except FileNotFoundError:
            c1h, fund = pd.DataFrame(columns=["open", "high", "low", "close", "volume"]), pd.DataFrame(columns=["funding_rate"])
        for _, t in grp.iterrows():
            rows.append({**t[["pair", "open_date", "is_short", "profit_ratio", "min_rate", "open_rate"]].to_dict(),
                         **features(t.to_dict(), c1h, fund)})
    df = gates(pd.DataFrame(rows))
    df["usdt"] = df["profit_ratio"] * STAKE
    df["half"] = np.where(df["open_date"] < pd.Timestamp("2025-07-01", tz="UTC"), "2024-04..2025-06", "2025-07..2026-09")
    deep = (~df["is_short"]) & (df["min_rate"] / df["open_rate"] - 1 <= -0.077)
    worst = df[deep & (df["usdt"] <= 0)]
    df.to_csv(OUT / "trades.csv", index=False)
    rep = {"all": summary(df), "coverage": {c: int(df[c].notna().sum()) for c in
                                            ("pump24", "volspike24", "funding_z", "oi_rise24", "oi_chg4")},
           "worst_deep_losers": int(len(worst)), "gates": {}}
    for g in ("G1_pumpdump", "G2_oispike", "G3_crowded_long", "G4_crowded_short"):
        fired = df[df[g]]
        rep["gates"][g] = {"fired": summary(fired), "not_fired": summary(df[~df[g]]),
                           "skip_effect_usdt": round(float(-fired["usdt"].sum()), 2),
                           "by_half": {h: round(float(-fired[fired["half"] == h]["usdt"].sum()), 2) for h in sorted(df["half"].unique())},
                           "fired_by_half": {h: int((fired["half"] == h).sum()) for h in sorted(df["half"].unique())},
                           "worst_losers_skipped": int(worst[g].sum()),
                           "fired_list": fired.sort_values("usdt")[["pair", "open_date", "usdt"]].astype(str).values.tolist()[:40]}
    (OUT / "report.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items() if k != "gates"}, default=str))
    for g, v in rep["gates"].items():
        print(g, "fired", v["fired"], "| skip effect", v["skip_effect_usdt"], v["by_half"], "| worst skipped",
              v["worst_losers_skipped"], flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
