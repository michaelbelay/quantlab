"""Validation part B: the cloud sweep's daily portfolio strategies on the 280 unseen coins.

Pre-registered in research/pipeline/focus/VALIDATE_2026-10-04_promising.md (part B).
Same engine, same strategy code and parameters as research/cloud_sweep_2026-09-25 - only the
coin universe changes. The daily panel is built one coin at a time with the same rules as the
cloud engine's load_daily (last close of the day, >= 20 hourly closes, funding shifted so an event
at 00:00 belongs to the day that ends there), because the 1h panel for 280 coins does not fit in memory.

    .venv\\Scripts\\python.exe research\\pipeline\\validate_daily.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CLOUD = ROOT / "research" / "cloud_sweep_2026-09-25"
sys.path.insert(0, str(CLOUD))
import engine as E  # noqa: E402  (load_daily/split use cloud paths and are NOT called)
import strats as S  # noqa: E402
from overlay import blend, vt  # noqa: E402

FUT = ROOT / "data" / "market" / "dev_1h" / "binance" / "futures"
OOS = ROOT / "data" / "market" / "extra_coins_1h"
OUT = HERE / "validate_daily_results.json"
STATUS_LOG = ROOT / "research" / "registry" / "status_log.jsonl"


def daily_from_hourly(k: pd.DataFrame, fund: pd.DataFrame | None) -> dict:
    k = k.copy()
    k["date"] = pd.to_datetime(k["date"], utc=True)
    k = k.set_index("date").sort_index()
    idx = pd.date_range(k.index.min().floor("D"), k.index.max().ceil("D") - pd.Timedelta(hours=1), freq="h", tz="UTC")
    k = k.reindex(idx)
    out = {"close": k["close"].resample("1D").last(), "high": k["high"].resample("1D").max(),
           "low": k["low"].resample("1D").min(), "qvol": (k["volume"] * k["close"]).resample("1D").sum(min_count=1)}
    n = k["close"].notna().resample("1D").sum()
    out["close"] = out["close"].where(n >= 20)
    f = pd.Series(0.0, index=idx)
    if fund is not None and len(fund):
        fs = fund.copy()
        fs["date"] = pd.to_datetime(fs["date"], utc=True).dt.floor("h")
        fs = fs.groupby("date")["funding_rate"].sum()
        f = fs.reindex(idx).fillna(0.0)
    out["funding"] = f.shift(-1).resample("1D").sum().reindex(out["close"].index).fillna(0.0)
    return out


def build_panel(coins: list[tuple[str, Path, Path]]) -> dict:
    cols = {k: {} for k in ("close", "high", "low", "qvol", "funding")}
    for name, p, fp in coins:
        k = pd.read_feather(p)
        if "date" not in k.columns or len(k) < 24 * 30:
            continue
        fund = pd.read_feather(fp) if fp.exists() else None
        d = daily_from_hourly(k, fund)
        for key in cols:
            cols[key][name] = d[key]
    D = {k: pd.DataFrame(v).sort_index() for k, v in cols.items()}
    idx = D["close"].index
    for k in D:
        D[k] = D[k].reindex(idx)
    D["funding"] = D["funding"].fillna(0.0)
    D["ret"] = D["close"].pct_change(fill_method=None)
    return D


def strategies(D, coins):
    p_mom = S.xs_mom(D, coins, lb=14, skip=1, n=5, every=14)
    p_carry = S.carry(D, coins, lb=7, n=8, every=7, ivol=True)
    p_trend = S.ts_trend(D, coins, lb=20, target_vol=0.3, long_only=True, every=1, method="ema")
    return {
        "TREND_GATED": S.trend_gated(D, coins, lb=20, n_sma=50, every=1, method="ret"),
        "XS_MOM_LONG+VT": vt(S.xs_mom(D, coins, lb=14, skip=1, n=5, every=14, long_only=True, btc_filter=True), D),
        "BLEND(MOM,CARRY,TREND)+VT": blend([p_mom, p_carry, p_trend], D),
    }


def verdict(r: dict) -> tuple[bool, list[str]]:
    fails = []
    if not (r["pf"] >= 1.10):
        fails.append(f"PF {r['pf']:.2f} < 1.10")
    if not (r["pf_2xcost"] >= 1.05):
        fails.append(f"PF at 2x costs {r['pf_2xcost']:.2f} < 1.05")
    if not (abs(r["maxdd"]) <= 0.40):
        fails.append(f"max drawdown {abs(r['maxdd']):.0%} > 40%")
    pos = sum(1 for k in ("reg_2021", "reg_2022", "reg_2023_24", "reg_2025_26") if r[k] > 0)
    if pos < 3:
        fails.append(f"only {pos}/4 regimes positive")
    return not fails, fails


def main() -> int:
    kept = json.loads((HERE / "oos_universe.json").read_text(encoding="utf-8"))["kept"]
    oos = [(s[:-4], OOS / s / "ohlcv_1h.feather", OOS / s / "funding.feather") for s in kept
           if (OOS / s / "ohlcv_1h.feather").exists()]
    btc = [("BTC", FUT / "BTC_USDT_USDT-1h-futures.feather", FUT / "BTC_USDT_USDT-1h-funding_rate.feather")]
    D = build_panel(oos + btc)
    coins = [c for c in D["close"].columns if c != "BTC"]          # BTC is the regime gate only
    print(f"daily panel: {len(coins)} unseen coins + BTC gate, {D['close'].index[0].date()} -> {D['close'].index[-1].date()}", flush=True)
    results = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "coins": len(coins), "rows": []}
    for label, W in strategies(D, coins).items():
        rep, r = E.full_report(W, D, label)
        rep = {k: (float(v) if isinstance(v, (np.floating, float, int, np.integer)) else v) for k, v in rep.items()}
        rep["gross_mean"] = float(W.abs().sum(axis=1).loc["2021-03":].mean())
        ok, fails = verdict(rep)
        rep["pass"], rep["fails"] = ok, fails
        results["rows"].append(rep)
        print(f"{label:28} PF {rep['pf']:.3f}  2x {rep['pf_2xcost']:.3f}  DD {abs(rep['maxdd']):.1%}  CAGR {rep['cagr']:.1%}  "
              f"Sharpe {rep['sharpe']:.2f}  regimes 2021 {rep['reg_2021']:+.1%} 2022 {rep['reg_2022']:+.1%} "
              f"23-24 {rep['reg_2023_24']:+.1%} 25-26 {rep['reg_2025_26']:+.1%}  trades {rep['trades']}  -> "
              f"{'PASS' if ok else 'FAIL: ' + '; '.join(fails)}", flush=True)
    OUT.write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
    with open(STATUS_LOG, "a", encoding="utf-8") as f:
        for rep in results["rows"]:
            status = "VALIDATED" if rep["pass"] else "REJECTED"
            reason = (f"Validation on {len(coins)} unseen coins (VALIDATE_2026-10-04_promising.md part B): "
                      + ("passed every bar - eligible for a paper forward test only." if rep["pass"] else "failed " + "; ".join(rep["fails"]) + ".")
                      + f" PF {rep['pf']:.2f}, 2x costs {rep['pf_2xcost']:.2f}, max DD {abs(rep['maxdd']):.0%}, CAGR {rep['cagr']:.1%}.")
            f.write(json.dumps({"id": f"cloud:{rep['label']}", "status": status, "reason": reason, "at": results["run_at"],
                                "source": "research/pipeline/validate_daily.py"}) + "\n")
    print("VALIDATE_DAILY_COMPLETE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
