"""VBreak4 by market condition - runner for PREREGISTRATION_2026-10-11_vbreak_conditions.md (read that first).

    C:\\quantlab\\.venv\\Scripts\\python.exe research\\vbreak_conditions.py      (cwd = C:\\quantlab)

Frozen VBreak4Both trades (dev + oos, 2026-10-04) -> point-in-time top-133 liquidity filter -> BTC condition at entry
-> trade-level stats + 300 USDT book replay per cell. Writes VBREAK_CONDITIONS_RESULT_2026-10-11.{md,json}.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, r"C:\quantlab")
from quant.book import metrics, replay  # noqa: E402

TR = ROOT / "research" / "pipeline" / "trades"
OUT = ROOT / "research" / "VBREAK_CONDITIONS_RESULT_2026-10-11"
TOP = 133
CELLS = ["Bull-Calm", "Bull-Wild", "Bear-Calm", "Bear-Wild"]
YEARS = [(str(y), f"{y}-01-01", f"{y + 1}-01-01") for y in range(2021, 2027)]


def btc_conditions() -> pd.DataFrame:
    spot = pd.read_feather(ROOT / "data" / "market" / "oot" / "BTCUSDT_1d.feather")[["date", "close"]]
    fut = pd.read_feather(ROOT / "data" / "market" / "dev_1h" / "binance" / "futures" / "BTC_USDT_USDT-1d-futures.feather")[["date", "close"]]
    d = pd.concat([spot[spot.date < fut.date.min()], fut]).drop_duplicates("date").set_index("date")["close"].sort_index()
    ret20 = d / d.shift(20) - 1
    vol20 = d.pct_change().rolling(20).std()
    med365 = vol20.rolling(365, min_periods=300).median().shift(1)        # previous 365 days
    c = pd.DataFrame({"bull": ret20 > 0, "wild": vol20 > med365, "ok": ret20.notna() & med365.notna()})
    c.index = c.index + pd.Timedelta(days=1)          # a daily candle dated D closes at D+1 00:00: usable from then
    return c


def min_notional() -> dict:
    d = json.load(open(ROOT / "research" / "results" / "min_notional_mainnet.json", encoding="utf-8"))
    out = {}
    for r in d["rows"]:
        coin = r["pair"].split("/")[0]
        out[coin] = max(float(r.get("cost_min") or 0), float(r.get("notional_filter") or 0)) or 5.0
    return out


def load_trades() -> pd.DataFrame:
    t = pd.concat([pd.read_parquet(TR / "focus-val1-vbreak4both__dev.parquet").assign(set="dev"),
                   pd.read_parquet(TR / "focus-val1-vbreak4both__oos.parquet").assign(set="oos")], ignore_index=True)
    t["entry_date"] = pd.to_datetime(t["entry_date"], utc=True).astype("datetime64[ns, UTC]")
    t["exit_date"] = pd.to_datetime(t["exit_date"], utc=True).astype("datetime64[ns, UTC]")
    return t


def tag(t: pd.DataFrame) -> pd.DataFrame:
    liq = pd.read_parquet(r"C:\quantlab\data\liq_rank.parquet")
    liq.index = pd.to_datetime(liq.index, utc=True).astype("datetime64[ns, UTC]")
    day = t["entry_date"].dt.floor("D")
    ranks = np.full(len(t), np.nan)
    pos = liq.index.get_indexer(day)
    for i, (p, coin) in enumerate(zip(pos, t["pair"])):
        if p >= 0 and coin in liq.columns:
            ranks[i] = liq.iat[p, liq.columns.get_loc(coin)]
    t["liq_rank"] = ranks
    c = btc_conditions()
    c.index = pd.to_datetime(c.index, utc=True).astype("datetime64[ns, UTC]")
    cc = c.reindex(c.index.union(t["entry_date"].dt.floor("D").unique())).ffill()
    # condition known at entry: last completed daily close strictly before the entry time
    known = cc.reindex(t["entry_date"].dt.floor("D")).reset_index(drop=True)
    t["bull"], t["wild"], t["cond_ok"] = known["bull"].astype(bool).values, known["wild"].astype(bool).values, known["ok"].fillna(False).astype(bool).values
    t["cell"] = np.where(t["bull"], "Bull", "Bear") + "-" + np.where(t["wild"], "Wild", "Calm")
    return t


def trade_stats(t: pd.DataFrame) -> dict:
    def pf(x):
        loss = -x[x < 0].sum()
        return round(float(x[x > 0].sum() / loss), 3) if loss > 0 else None
    p, p2 = t["pnl"], t["pnl"] - 0.20
    years = {}
    for y, a, b in YEARS:
        w = t[(t["entry_date"] >= a) & (t["entry_date"] < b)]
        years[y] = {"n": int(len(w)), "pnl": round(float(w["pnl"].sum()), 1), "pf": pf(w["pnl"]) if len(w) else None}
    elig = {y: v for y, v in years.items() if v["n"] >= 20}
    return {"trades": int(len(t)), "pf": pf(p), "pf_x2": pf(p2), "avg_pct": round(float(p.mean()), 3) if len(t) else None,
            "long": {"n": int((t.side == "long").sum()), "pf": pf(p[t.side == "long"])},
            "short": {"n": int((t.side == "short").sum()), "pf": pf(p[t.side == "short"])},
            "years": years, "years_eligible": len(elig), "years_positive": sum(v["pnl"] > 0 for v in elig.values())}


def book(t: pd.DataFrame, mn: dict) -> dict:
    b = pd.DataFrame({"entry_t": t["entry_date"], "exit_t": t["exit_date"], "coin": t["pair"],
                      "side": np.where(t["side"] == "long", 1, -1), "ret": t["pnl"] / t["notional"],
                      "mae": 0.0, "reason": "na"})
    tk, curve = replay(b, mn)
    m = metrics(tk, curve, YEARS)
    return {k: m.get(k) for k in ("final", "max_dd_pct", "cagr_pct", "trades", "pf", "periods", "worst_year_pct")}


def verdict(s: dict, b: dict) -> dict:
    g = {"trades>=200": s["trades"] >= 200, "pf>=1.15": (s["pf"] or 0) >= 1.15, "pf_x2>=1.05": (s["pf_x2"] or 0) >= 1.05,
         "years>=2/3": s["years_eligible"] > 0 and s["years_positive"] >= 2 / 3 * s["years_eligible"],
         "book>300": (b.get("final") or 0) > 300, "book_dd<=40%": (b.get("max_dd_pct") or 999) <= 40}
    g["PASS"] = all(g.values())
    return g


def main() -> None:
    t = tag(load_trades())
    n_all = len(t)
    t = t[t["cond_ok"]]
    fair = t[t["liq_rank"] <= TOP].copy()
    mn = min_notional()
    out = {"preregistration_sha256": (ROOT / "research" / "PREREGISTRATION_2026-10-11_vbreak_conditions.md.sha256").read_text().split()[0],
           "trades_recorded": n_all, "trades_with_condition": int(len(t)), "trades_top133": int(len(fair)),
           "top133_from_dev_list": int((fair["set"] == "dev").sum()), "top133_from_oos_list": int((fair["set"] == "oos").sum()),
           "cells": {}}
    groups = {"ALL (top-133, every condition)": fair, "Bull": fair[fair.bull], "Bear": fair[~fair.bull]}
    groups.update({c: fair[fair.cell == c] for c in CELLS})
    for name, g in groups.items():
        s, b = trade_stats(g), book(g, mn)
        out["cells"][name] = {"trades": s, "book": b, "gates": verdict(s, b) if name in CELLS else None}
        print(name, s["trades"], s["pf"], s["pf_x2"], b.get("final"), b.get("max_dd_pct"),
              out["cells"][name]["gates"]["PASS"] if name in CELLS else "", flush=True)
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
