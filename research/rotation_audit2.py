"""Data-only audit for the rotation test (requested 2026-09-28 before any amendment).

Reads dates, volumes and archive file listings only. Computes no returns and
imports nothing from rotation_run.py.

  1. Last TRADED bar per symbol (volume > 0) -> corrected dead-contract count.
  2. Every no-trading run > 24 h (zero-volume bars and missing bars together),
     bucketed 1-6 days (24 h < len < 7 d) / 7+ days (>= 7 d), resumed or not.
  3. Bound on cut-short history: earliest/latest evidence of each contract from
     other archive datasets, Binance onboardDate (listed contracts) and the REST
     funding history (delisted contracts), versus where the 1h klines start/end.

    .venv\\Scripts\\python.exe research\\rotation_audit2.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rotation_data import s3_list  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "market" / "rotation"
OUT = ROOT / "research" / "results"
WIN_START = pd.Timestamp("2021-01-01", tz="UTC")
DATA_END = pd.Timestamp("2026-09-25 23:00", tz="UTC")
DEAD_MARGIN = pd.Timedelta(days=2)
DAY, WEEK = pd.Timedelta(hours=24), pd.Timedelta(days=7)

SOURCES = {
    "klines_1h": "data/futures/um/monthly/klines/{s}/1h/",
    "klines_1d": "data/futures/um/monthly/klines/{s}/1d/",
    "fundingRate": "data/futures/um/monthly/fundingRate/{s}/",
    "markPrice_1h": "data/futures/um/monthly/markPriceKlines/{s}/1h/",
    "aggTrades": "data/futures/um/monthly/aggTrades/{s}/",
}


def month_span(sym: str) -> dict:
    out = {}
    for name, pre in SOURCES.items():
        try:
            keys = s3_list(pre.format(s=sym), delimiter=None)
        except Exception as e:
            out[name] = {"error": str(e)[:80]}
            continue
        ms = sorted(set(m.group(1) for m in (re.search(r"-(\d{4}-\d{2})\.zip$", k) for k in keys) if m))
        out[name] = {"first": ms[0], "last": ms[-1], "months": len(ms)} if ms else None
    return out


def runs_for(sym: str) -> tuple[dict, list]:
    k = pd.read_parquet(DATA / sym / "klines_1h.parquet")      # an empty file has no columns
    if not len(k) or "volume" not in k:
        return {"symbol": sym, "bars": 0}, []
    traded = k.loc[k["volume"] > 0, "date"].reset_index(drop=True)
    rec = {"symbol": sym, "bars": len(k), "first_bar": k["date"].iloc[0], "last_bar": k["date"].iloc[-1],
           "first_traded": traded.iloc[0] if len(traded) else None,
           "last_traded": traded.iloc[-1] if len(traded) else None}
    runs = []
    if not len(traded):
        return rec, runs
    zero_set = set(k.loc[k["volume"] == 0, "date"])
    # gaps between consecutive traded bars; the no-trading time is gap - 1 h
    g = traded.diff()
    for i in range(1, len(traded)):
        nt = g.iloc[i] - pd.Timedelta(hours=1)
        if nt > DAY:
            a, b = traded.iloc[i - 1], traded.iloc[i]
            hours = int(nt / pd.Timedelta(hours=1))
            zero_h = sum(1 for h in pd.date_range(a + pd.Timedelta(hours=1), b - pd.Timedelta(hours=1), freq="1h")
                         if h in zero_set)
            runs.append({"symbol": sym, "last_traded_before": a, "next_traded": b, "hours": hours,
                         "bucket": "7+ days" if nt >= WEEK else "1-6 days", "resumed": True,
                         "zero_volume_hours": zero_h, "missing_hours": hours - zero_h})
    tail = k["date"].iloc[-1] - traded.iloc[-1]
    if tail > DAY:   # trailing no-trading stretch up to the end of the file
        a = traded.iloc[-1]
        zero_h = int(((k["date"] > a) & (k["volume"] == 0)).sum())
        hours = int(tail / pd.Timedelta(hours=1))
        runs.append({"symbol": sym, "last_traded_before": a, "next_traded": None, "hours": hours,
                     "bucket": "7+ days" if tail >= WEEK else "1-6 days", "resumed": False,
                     "zero_volume_hours": zero_h, "missing_hours": hours - zero_h})
    return rec, runs


def rest_first_funding(sym: str):
    for attempt in range(3):
        try:
            r = requests.get("https://fapi.binance.com/fapi/v1/fundingRate",
                             params={"symbol": sym, "startTime": 1546300800000, "limit": 1}, timeout=20)
            if r.status_code == 429:
                time.sleep(30)
                continue
            j = r.json()
            if isinstance(j, list) and j:
                return pd.to_datetime(int(j[0]["fundingTime"]), unit="ms", utc=True)
            return None
        except Exception:
            time.sleep(3)
    return "error"


def main():
    t0 = time.time()
    syms = json.loads((DATA / "symbols.json").read_text(encoding="utf-8"))["symbols"]

    # ---- 1 + 2: traded bars and no-trading runs
    recs, runs = [], []
    for s in syms:
        r, rr = runs_for(s)
        recs.append(r)
        runs += rr
    print(f"runs computed ({time.time() - t0:.0f}s)", flush=True)

    # ---- 3: evidence of existence
    info = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo", timeout=30).json()
    onboard = {s["symbol"]: pd.to_datetime(int(s["onboardDate"]), unit="ms", utc=True) for s in info["symbols"]
               if s.get("contractType") == "PERPETUAL"}
    cache = OUT / "rotation_audit2_evidence_cache.json"
    if cache.exists():
        c = json.loads(cache.read_text(encoding="utf-8"))
        spans = c["spans"]
        rest = {s: (pd.Timestamp(v) if v not in (None, "error") else v) for s, v in c["rest"].items()}
        print("evidence loaded from cache", flush=True)
    else:
        with ThreadPoolExecutor(16) as pool:
            spans = dict(zip(syms, pool.map(month_span, syms)))
        print(f"archive spans listed ({time.time() - t0:.0f}s)", flush=True)
        rest = {}
        for s in syms:
            if s not in onboard:                    # delisted: no onboardDate, ask the funding history
                rest[s] = rest_first_funding(s)
                time.sleep(0.7)                    # stay well inside the endpoint's 500 / 5 min limit
        print(f"REST funding checked for {len(rest)} delisted symbols ({time.time() - t0:.0f}s)", flush=True)
        OUT.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"spans": spans, "rest": {s: (str(v) if isinstance(v, pd.Timestamp) else v)
                                                              for s, v in rest.items()}}, indent=1), encoding="utf-8")

    rows = []
    for r in recs:
        s = r["symbol"]
        ev_first, ev_last, src_first = [], [], {}
        for name, sp in spans[s].items():
            if sp and "first" in sp:
                f = pd.Timestamp(sp["first"] + "-01", tz="UTC")
                l = pd.Timestamp(sp["last"] + "-01", tz="UTC") + pd.offsets.MonthEnd(1)
                ev_first.append(f)
                ev_last.append(l)
                src_first[name] = sp["first"]
        if s in onboard:
            ev_first.append(onboard[s])
            src_first["onboardDate"] = str(onboard[s].date())
        rf = rest.get(s)
        if isinstance(rf, pd.Timestamp):
            ev_first.append(rf)
            src_first["rest_funding"] = str(rf.date())
        e_first = min(ev_first) if ev_first else None
        e_last = max(ev_last) if ev_last else None
        fb = r.get("first_bar")
        existed_at_start = bool(e_first is not None and e_first < WIN_START + pd.Timedelta(days=31)
                                and (e_last is None or e_last >= WIN_START))
        covered_at_start = bool(fb is not None and fb < WIN_START + pd.Timedelta(days=31))
        # cut short at the start: evidence before the window/first bar by more than a month
        cut_start = bool(fb is not None and e_first is not None
                         and max(e_first, WIN_START) < fb - pd.Timedelta(days=31))
        lt = r.get("last_traded")
        dead = bool(lt is not None and lt < DATA_END - DEAD_MARGIN)
        rows.append({"symbol": s, "listed_today": s in onboard, "first_bar": str(fb) if fb is not None else None,
                     "last_bar": str(r.get("last_bar")) if r.get("last_bar") is not None else None,
                     "last_traded": str(lt) if lt is not None else None, "dead": dead,
                     "evidence_first": str(e_first) if e_first is not None else None,
                     "evidence_first_by_source": src_first,
                     "existed_at_2021_01": existed_at_start, "klines_cover_2021_01": covered_at_start,
                     "cut_short_at_start": cut_start})

    df = pd.DataFrame(rows)
    rdf = pd.DataFrame(runs)
    old_dead = int(sum(1 for r in recs if r.get("last_bar") is not None and r["last_bar"] < DATA_END - DEAD_MARGIN))
    ex = df[df["existed_at_2021_01"]]
    summary = {
        "symbols": len(df),
        "dead_by_last_bar_OLD_METRIC": old_dead,
        "dead_by_last_traded_bar": int(df["dead"].sum()),
        "dead_but_listed_today": int((df["dead"] & df["listed_today"]).sum()),
        "not_listed_today": int((~df["listed_today"]).sum()),
        "runs_over_24h": len(rdf),
        "runs_by_bucket": {f"{b} / {'resumed' if r_ else 'never resumed'}": int(n)
                           for (b, r_), n in rdf.groupby(["bucket", "resumed"]).size().items()} if len(rdf) else {},
        "symbols_with_runs": int(rdf["symbol"].nunique()) if len(rdf) else 0,
        "existed_at_2021_01_all_evidence": int(len(ex)),
        "of_which_klines_cover_2021_01": int(ex["klines_cover_2021_01"].sum()),
        "coverage_ratio_2021_01_incl_dead": round(float(ex["klines_cover_2021_01"].mean()), 4) if len(ex) else None,
        "existed_at_2021_01_dead": int(ex["dead"].sum()),
        "existed_at_2021_01_dead_covered": int((ex["dead"] & ex["klines_cover_2021_01"]).sum()),
        "cut_short_at_start_any_time": int(df["cut_short_at_start"].sum()),
        "cut_short_list": df.loc[df["cut_short_at_start"], ["symbol", "first_bar", "evidence_first", "listed_today"]]
                            .to_dict("records"),
        "missing_2021_01_but_existed": ex.loc[~ex["klines_cover_2021_01"], ["symbol", "first_bar", "evidence_first",
                                                                            "listed_today"]].to_dict("records"),
        "rest_funding_errors": [s for s, v in rest.items() if v == "error"],
        "limits": "Contracts with no file in ANY archive dataset, no onboardDate (delisted) and no REST funding "
                  "history are invisible to every source used here; the bound cannot include them.",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rotation_audit2.json").write_text(json.dumps({"summary": summary, "symbols": rows,
                                                          "runs": rdf.astype(str).to_dict("records")},
                                                         indent=1, default=str), encoding="utf-8")
    rdf.to_csv(OUT / "rotation_audit2_runs.csv", index=False)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("cut_short_list", "missing_2021_01_but_existed")},
                     indent=1, default=str))
    print(f"seconds: {time.time() - t0:.0f}")


if __name__ == "__main__":
    main()
