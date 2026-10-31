"""VBreak4 shorts in Bear-Calm on coins VBreak4 never ran on - runner for PREREGISTRATION_2026-10-11_bearcalm_fresh.md.

    .venv\\Scripts\\python.exe research\\bearcalm_fresh.py --download     (cwd = C:\\quantlab) public 1h OHLCV
    .venv\\Scripts\\python.exe research\\bearcalm_fresh.py --run          the one registered run

Writes research/bearcalm_fresh/{coins.json, trades.parquet, result.json} and BEARCALM_FRESH_RESULT_2026-10-11.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "research"), str(ROOT / "research" / "engine"), r"C:\quantlab"]
from desk_data import ARCHIVE, KLINE_COLS, _frame, fetch_zip_csv  # noqa: E402
from rotation_data import END, START, STABLE_BASES, s3_list  # noqa: E402

HERE = ROOT / "research" / "bearcalm_fresh"
ROT = ROOT / "data" / "market" / "rotation"
DATA = ROOT / "data" / "market" / "fresh"
PREREG = ROOT / "research" / "PREREGISTRATION_2026-10-11_bearcalm_fresh.md"
RESULT_MD = ROOT / "research" / "BEARCALM_FRESH_RESULT_2026-10-11.md"
TOP, PERIOD = 133, ("2024-01-01", "2026-09-26")
YEARS = [(str(y), f"{y}-01-01", f"{y + 1}-01-01") for y in (2024, 2025, 2026)]
SPEC = {"family": "volatility_breakout", "params": {"bars": 4, "atr_mult": 2.0}, "filters": ["btc_regime", "volume"],
        "trend_mode": "with", "direction": "short", "min_score": 0.0, "regime": None}
CFG = {"leverage": 1.0, "stop_mode": "atr", "stop_atr": 2.0, "tp_mode": "none", "tp_atr": [], "tp_frac": [],
       "entry_mode": "instant", "max_bars": 400}
INDEX_BASES = {"BTCDOM", "DEFI", "BFUSD"}


def dev_coins() -> set[str]:
    return set(pd.read_parquet(ROOT / "research" / "pipeline" / "trades" / "focus-val1-vbreak4both__dev.parquet").pair.unique())


def oos_syms() -> set[str]:
    return set(json.loads((ROOT / "research" / "pipeline" / "oos_universe.json").read_text(encoding="utf-8"))["kept"])


def select() -> list[str]:
    dev, oos = dev_coins(), oos_syms()
    ut = json.loads((ROOT / "research" / "pipeline" / "exchangeinfo_underlying_2026-10-04.json").read_text(encoding="utf-8"))
    out = []
    for d in sorted(p for p in ROT.iterdir() if p.is_dir()):
        s, b = d.name, d.name[:-4]
        if not s.endswith("USDT") or b in dev or s in oos or b in STABLE_BASES or b in INDEX_BASES:
            continue
        if ut.get(s) not in (None, "COIN"):
            continue
        try:
            n = len(pd.read_parquet(d / "klines_1h.parquet"))
        except Exception:
            n = 0
        if n >= 400:
            out.append(s)
    return out


def get(sym: str, pool: ThreadPoolExecutor) -> str:
    out = DATA / sym
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


def download() -> int:
    HERE.mkdir(parents=True, exist_ok=True)
    cf = HERE / "coins.json"
    coins = json.loads(cf.read_text(encoding="utf-8")) if cf.exists() else select()
    if not cf.exists():
        cf.write_text(json.dumps(coins, indent=0, ensure_ascii=False), encoding="utf-8")
    print(f"{len(coins)} fresh coins", flush=True)
    with ThreadPoolExecutor(8) as pool:
        for i, s in enumerate(coins, 1):
            try:
                r = get(s, pool)
            except Exception as e:
                r = f"FAILED {type(e).__name__}: {e}"
            print(f"[{i}/{len(coins)}] {s}: {r}", flush=True)
    print("FRESH_DATA_COMPLETE", flush=True)
    return 0


def liq_rank(syms: list[str]) -> pd.DataFrame:
    """Same formula as quantlab quant/liquidity.py, across every crypto coin: 30-day average daily quote volume,
    yesterday and before only, rank 1 = most traded."""
    cols = {}
    for s in syms:
        p = ROT / s / "klines_1h.parquet"
        try:
            k = pd.read_parquet(p, columns=["date", "quote_volume"])
        except Exception:
            continue
        cols[s] = k.set_index("date")["quote_volume"].resample("1D").sum(min_count=1)
    daily = pd.DataFrame(cols)
    avg30 = daily.rolling(30, min_periods=20).mean().shift(1)
    return avg30.rank(axis=1, ascending=False)


def pf(x: pd.Series):
    loss = -x[x < 0].sum()
    return round(float(x[x > 0].sum() / loss), 3) if loss > 0 else None


def run() -> int:
    import backtest as BT
    from backtest import Config, simulate_pair
    from features import PairFeatures
    from quant.book import metrics, replay
    from vbreak_conditions import btc_conditions, min_notional

    sha = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    coins = json.loads((HERE / "coins.json").read_text(encoding="utf-8"))
    cfg = Config()
    for k, v in CFG.items():
        setattr(cfg, k, tuple(v) if isinstance(v, list) else v)
    rows, missing = [], []
    for i, s in enumerate(coins, 1):
        p = DATA / s / "ohlcv_1h.feather"
        if not p.exists():
            missing.append(s)
            continue
        df = pd.read_feather(p)
        if len(df) < 400:
            missing.append(s)
            continue
        fp = DATA / s / "funding.feather"
        f = PairFeatures(df, pd.read_feather(fp) if fp.exists() else None)
        dates = pd.to_datetime(f.date, utc=True)
        for t in simulate_pair(f, SPEC, cfg, s[:-4]):
            rows.append((s, t.pnl, "long" if t.side > 0 else "short", dates[t.entry_i],
                         dates[min(t.exit_i, len(dates) - 1)], t.bars, t.notional))
        if i % 25 == 0:
            print(f"  simulated {i}/{len(coins)}", flush=True)
    t = pd.DataFrame(rows, columns=["pair", "pnl", "side", "entry_date", "exit_date", "bars", "notional"])
    for c in ("entry_date", "exit_date"):
        t[c] = pd.to_datetime(t[c], utc=True).astype("datetime64[ns, UTC]")
    n_engine = len(t)

    # point-in-time liquidity rank across all crypto coins (dev + unseen + fresh)
    every = sorted({c + "USDT" for c in dev_coins()} | oos_syms() | set(coins))
    rank = liq_rank(every)
    rank.index = pd.to_datetime(rank.index, utc=True).astype("datetime64[ns, UTC]")
    day = t["entry_date"].dt.floor("D")
    pos = rank.index.get_indexer(day)
    t["liq_rank"] = [rank.iat[p, rank.columns.get_loc(s)] if p >= 0 and s in rank.columns else np.nan
                     for p, s in zip(pos, t["pair"])]
    cond = btc_conditions()
    cond.index = pd.to_datetime(cond.index, utc=True).astype("datetime64[ns, UTC]")
    cc = cond.reindex(cond.index.union(day.unique())).ffill()
    known = cc.reindex(day).reset_index(drop=True)
    t["cell"] = np.where(known["ok"].fillna(False).astype(bool),
                         np.where(known["bull"].astype(bool), "Bull", "Bear") + "-" + np.where(known["wild"].astype(bool), "Wild", "Calm"),
                         "unknown")
    t.to_parquet(HERE / "trades.parquet")

    inper = (t["entry_date"] >= pd.Timestamp(PERIOD[0], tz="UTC")) & (t["entry_date"] < pd.Timestamp(PERIOD[1], tz="UTC"))
    g = t[inper & (t["liq_rank"] <= TOP) & (t["cell"] == "Bear-Calm")].copy()

    years = {}
    for y, a, b in YEARS:
        w = g[(g["entry_date"] >= a) & (g["entry_date"] < b)]
        years[y] = {"n": int(len(w)), "pnl": round(float(w["pnl"].sum()), 2), "pf": pf(w["pnl"]) if len(w) else None}
    elig = {y: v for y, v in years.items() if v["n"] >= 20}
    daysum = g.groupby(g["entry_date"].dt.floor("D"))["pnl"].sum().sort_values(ascending=False)
    wo3 = float(daysum.iloc[3:].sum()) if len(daysum) > 3 else None
    coin = g.groupby("pair")["pnl"].sum().sort_values(ascending=False)

    mn = min_notional()
    mn = {s: mn.get(s[:-4], 5.0) for s in coins}
    bk = pd.DataFrame({"entry_t": g["entry_date"], "exit_t": g["exit_date"], "coin": g["pair"], "side": -1,
                       "ret": g["pnl"] / g["notional"], "mae": 0.0, "reason": "na"})
    if len(bk):
        tk, curve = replay(bk, mn)
        m = metrics(tk, curve, YEARS)
        book = {k: m.get(k) for k in ("final", "max_dd_pct", "cagr_pct", "trades", "pf", "periods", "worst_year_pct")}
    else:
        book = {"final": None, "max_dd_pct": None, "trades": 0}

    s = {"trades": int(len(g)), "pf": pf(g["pnl"]), "pf_x2": pf(g["pnl"] - 0.20), "net": round(float(g["pnl"].sum()), 2),
         "avg_pct": round(float(g["pnl"].mean()), 3) if len(g) else None, "win_rate": round(float((g["pnl"] > 0).mean() * 100), 1) if len(g) else None,
         "years": years, "years_eligible": len(elig), "years_positive": sum(v["pnl"] > 0 for v in elig.values()),
         "net_without_best3_days": round(wo3, 2) if wo3 is not None else None, "entry_days": int(len(daysum)),
         "coins": int(coin.size), "coins_positive": int((coin > 0).sum()),
         "top5_coins": {k: round(float(v), 2) for k, v in coin.head(5).items()},
         "top5_share_of_profit": round(float(coin.head(5).clip(lower=0).sum() / coin[coin > 0].sum()), 3) if (coin > 0).any() else None}
    gates = {"trades>=100": s["trades"] >= 100, "pf>=1.15": (s["pf"] or 0) >= 1.15, "pf_x2>=1.05": (s["pf_x2"] or 0) >= 1.05,
             "years>=2/3": s["years_eligible"] > 0 and s["years_positive"] >= 2 / 3 * s["years_eligible"],
             "without_best3_days>0": (wo3 or 0) > 0,
             "book>300": (book.get("final") or 0) > 300, "book_dd<=30%": (book.get("max_dd_pct") if book.get("max_dd_pct") is not None else 999) <= 30}
    gates["PASS"] = all(gates.values())
    other = {c: {"n": int((x := t[inper & (t["liq_rank"] <= TOP) & (t["cell"] == c)]).shape[0]), "pf": pf(x["pnl"])}
             for c in ("Bull-Calm", "Bull-Wild", "Bear-Wild")}
    out = {"preregistration_sha256": sha, "coins": len(coins), "coins_missing_data": missing, "engine_trades_all": n_engine,
           "in_period_top133": int((inper & (t["liq_rank"] <= TOP)).sum()), "bear_calm": s, "book": book, "gates": gates,
           "reported_other_cells_not_judged": other}
    (HERE / "result.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.download:
        return download()
    if a.run:
        if (HERE / "result.json").exists():
            print("already run once - the registration allows one run only")
            return 2
        return run()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
