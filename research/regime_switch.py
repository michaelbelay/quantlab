"""Regime-switching book test. Rules: research/PREREGISTRATION_2026-10-07_regime_switch.md (frozen, do not edit).

  .venv\\Scripts\\python.exe research\\regime_switch.py fit     # fit window only -> regime_switch/choice.json
  .venv\\Scripts\\python.exe research\\regime_switch.py testA   # 133 development coins, 2024-01-01 .. 2026-09-18
  .venv\\Scripts\\python.exe research\\regime_switch.py testB   # 280 unseen coins, same window (only if A passed)

Reads only research/pipeline/trades/*__dev.parquet, the BTC 1d futures file and (testB) the unseen coins.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "regime_switch"
TRADES = HERE / "pipeline" / "trades"
BTC = ROOT / "data" / "market" / "dev_1h" / "binance" / "futures" / "BTC_USDT_USDT-1d-futures.feather"

FIT = ("2021-01-01", "2024-01-01")          # [start, end) on entry date
TEST = ("2024-01-01", "2026-09-19")         # entries 2024-01-01 .. 2026-09-18
FIT_HALVES = [("2021-01-01", "2023-01-01"), ("2023-01-01", "2024-01-01")]
TEST_YEARS = [("2024-01-01", "2025-01-01"), ("2025-01-01", "2026-01-01"), ("2026-01-01", "2026-09-19")]
TYPES = ["UP_LOVOL", "UP_HIVOL", "DN_LOVOL", "DN_HIVOL"]
EXTRA_COST = 0.2       # per trade on notional 100 = 2x costs
MIN_TRADES, MIN_PF, MIN_PF2, MIN_T, MIN_HALF = 100, 1.15, 1.05, 3.0, 20
TOP_K, MAX_OVERLAP = 3, 0.70
SEED, SHUFFLES, BLOCK = 20261007, 1000, 30


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def market_types() -> pd.Series:
    """Type of day D from BTC daily closes up to D-1 (index = UTC day)."""
    d = pd.read_feather(BTC)
    d["date"] = pd.to_datetime(d["date"], utc=True).astype("datetime64[ns, UTC]")
    c = d.set_index("date").close
    sma = c.rolling(50).mean()
    vol = np.log(c).diff().rolling(20).std()
    med = vol.rolling(365, min_periods=60).median()
    st = pd.Series(np.where(c > sma, "UP", "DN"), index=c.index) + pd.Series(np.where(vol > med, "_HIVOL", "_LOVOL"), index=c.index)
    st[sma.isna() | med.isna() | vol.isna()] = None
    return st.shift(1)


def tag(df: pd.DataFrame, types: pd.Series) -> pd.DataFrame:
    df = df.copy()
    df["entry_date"] = pd.to_datetime(df["entry_date"], utc=True).astype("datetime64[ns, UTC]")
    df["day"] = df.entry_date.dt.floor("D")
    df["type"] = df.day.map(types)
    return df


def window(df, a, b):
    return df[(df.entry_date >= ts(a)) & (df.entry_date < ts(b))]


def pf(p: np.ndarray):
    l = -p[p < 0].sum()
    return float(p[p > 0].sum() / l) if l > 0 else float("inf")


def day_t(day_pnl: pd.Series):
    x = day_pnl.to_numpy()
    if len(x) < 3 or x.std(ddof=1) == 0:
        return None
    return float(x.mean() / x.std(ddof=1) * np.sqrt(len(x)))


def keyset(df) -> set:
    return set(zip(df.pair, df.day, df.side))


# ------------------------------------------------------------------ fit
def fit():
    types = market_types()
    files = sorted(TRADES.glob("*__dev.parquet"))
    print(f"pool: {len(files)} candidates with development trades")
    cells, keep_keys = [], {}
    for f in files:
        cid = f.name.split("__")[0]
        df = window(tag(pd.read_parquet(f), types), *FIT)
        for ty in TYPES:
            x = df[df.type == ty]
            if len(x) < MIN_TRADES:
                continue
            p = x.pnl.to_numpy()
            row = {"id": cid, "type": ty, "trades": len(x), "pf": pf(p), "pf2": pf(p - EXTRA_COST),
                   "t": day_t(x.groupby("day").pnl.mean()), "net": float(p.sum())}
            halves = []
            for a, b in FIT_HALVES:
                h = window(x, a, b)
                halves.append(None if len(h) < MIN_HALF else float(h.pnl.sum()))
            row["half1"], row["half2"] = halves
            row["pass"] = bool(row["pf"] >= MIN_PF and row["pf2"] >= MIN_PF2 and (row["t"] or 0) >= MIN_T
                               and all(h is None or h > 0 for h in halves) and any(h is not None for h in halves))
            cells.append(row)
            if row["pass"]:
                keep_keys[(cid, ty)] = keyset(x)
    cells = pd.DataFrame(cells)
    OUT.mkdir(exist_ok=True)
    cells.to_csv(OUT / "fit_cells.csv", index=False)
    print(f"cells with >= {MIN_TRADES} trades: {len(cells)}; passing: {int(cells['pass'].sum()) if len(cells) else 0}")

    choice = {}
    for ty in TYPES:
        cand = cells[(cells.type == ty) & cells["pass"]].sort_values("t", ascending=False) if len(cells) else []
        kept = []
        for _, r in (cand.iterrows() if len(cand) else []):
            k = keep_keys[(r.id, ty)]
            if any(len(k & keep_keys[(o, ty)]) / max(1, len(k | keep_keys[(o, ty)])) > MAX_OVERLAP for o in kept):
                continue
            kept.append(r.id)
            if len(kept) == TOP_K:
                break
        choice[ty] = kept
    filled = sum(1 for v in choice.values() if v)
    names = {}
    import sqlite3
    con = sqlite3.connect(f"file:{HERE / 'pipeline' / 'pipeline.db'}?mode=ro", uri=True)
    for ids in choice.values():
        for i in ids:
            r = con.execute("select name, status, stage from candidates where id=?", (i,)).fetchone()
            names[i] = {"name": r[0], "status": r[1], "stage": r[2]} if r else None
    res = {"choice": choice, "types_filled": filled, "stop": filled < 2, "names": names,
           "selected_cells": cells[cells.apply(lambda r: r.id in choice.get(r.type, []), axis=1)].to_dict("records") if len(cells) else []}
    (OUT / "choice.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for ty in TYPES:
        print(f"  {ty}: {[(i, names[i]['name']) for i in choice[ty]] or 'CASH'}")
    print("STOP: fewer than 2 types filled" if res["stop"] else f"{filled}/4 types filled")


# ------------------------------------------------------------------ test
def load_choice():
    return json.loads((OUT / "choice.json").read_text(encoding="utf-8"))


def book(trades: dict, choice: dict, types_by_day: pd.Series) -> pd.DataFrame:
    """Weighted trades of the switching book. trades: id -> tagged df (test window)."""
    parts = []
    for ty, ids in choice.items():
        for i in ids:
            x = trades[i]
            x = x[x.day.map(types_by_day) == ty]
            parts.append(x.assign(w=x.pnl / len(ids), w2=(x.pnl - EXTRA_COST) / len(ids)))
    return pd.concat(parts) if parts else pd.DataFrame(columns=["day", "w", "w2", "entry_date"])


def evaluate(trades: dict, choice: dict, types: pd.Series, label: str) -> dict:
    days = pd.date_range(ts(TEST[0]), ts(TEST[1]) - pd.Timedelta(days=1), freq="D")
    real = types.reindex(days)
    b = book(trades, choice, real)
    daily = b.groupby("day").w.sum()
    res = {"scope": label, "trades": int(len(b)), "pf": pf(b.w.to_numpy()), "pf_2x": pf(b.w2.to_numpy()),
           "net": float(b.w.sum()), "day_t": day_t(daily),
           "years": {a[:4]: float(window(b, a, e).w.sum()) for a, e in TEST_YEARS},
           "per_day": float(b.w.sum() / len(days))}
    ids = sorted({i for v in choice.values() for i in v})
    allon = pd.concat([trades[i].assign(w=trades[i].pnl / len(ids)) for i in ids])
    res["no_switch_net"] = float(allon.w.sum())
    res["no_switch_per_day"] = float(allon.w.sum() / len(days))
    rng = np.random.default_rng(SEED)
    blocks = [real.iloc[i:i + BLOCK].to_numpy() for i in range(0, len(real), BLOCK)]
    tot = np.empty(SHUFFLES)
    for k in range(SHUFFLES):
        order = rng.permutation(len(blocks))
        lab = pd.Series(np.concatenate([blocks[j] for j in order]), index=days)
        tot[k] = book(trades, choice, lab).w.sum()
    res["random_pct"] = float((tot < res["net"]).mean() * 100)
    res["random_median"] = float(np.median(tot))
    res["per_type"] = {ty: float(b[b.day.map(real) == ty].w.sum()) for ty in TYPES}
    res["checks"] = {
        "A1 PF>=1.10 and PF2x>=1.00": res["pf"] >= 1.10 and res["pf_2x"] >= 1.00,
        "A2 day t>=2": (res["day_t"] or 0) >= 2.0,
        "A3 >=2 of 3 years positive": sum(v > 0 for v in res["years"].values()) >= 2,
        "A4 beats no-switch per day": res["per_day"] > res["no_switch_per_day"],
        "A5 random switch >= p95": res["random_pct"] >= 95.0,
    }
    res["pass"] = all(res["checks"].values())
    return res


def show(res):
    print(json.dumps({k: v for k, v in res.items()}, indent=1, default=str))


def testA():
    ch = load_choice()
    if ch["stop"]:
        print("fit stopped the test: fewer than 2 types filled"); return
    types = market_types()
    trades = {i: window(tag(pd.read_parquet(TRADES / f"{i}__dev.parquet"), types), *TEST)
              for i in {i for v in ch["choice"].values() for i in v}}
    res = evaluate(trades, ch["choice"], types, "A: 133 development coins")
    (OUT / "testA.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    show(res)


def testB():
    ch = load_choice()
    a = json.loads((OUT / "testA.json").read_text(encoding="utf-8"))
    if not a["pass"]:
        print("test A failed: test B is not run (pre-registration §5)"); return
    sys.path[:0] = [str(HERE / "engine"), str(HERE / "pipeline")]
    import sqlite3
    import run as R
    R.status = lambda **k: None
    R.log = lambda m: print(m, flush=True)
    con = sqlite3.connect(f"file:{HERE / 'pipeline' / 'pipeline.db'}?mode=ro", uri=True)
    ids = sorted({i for v in ch["choice"].values() for i in v})
    runs = []
    for i in ids:
        spec, cfg = con.execute("select spec, cfg from candidates where id=?", (i,)).fetchone()
        runs.append({"key": i, "spec": json.loads(spec), "cfg": json.loads(cfg), "cost_mult": 1.0, "random": False})
    seen = [i for i in ids if (TRADES / f"{i}__oos.parquet").exists()]
    out = R.run_pass("regime switch B", R.oos_coins(), runs, 1, SEED, 0)
    types = market_types()
    trades = {}
    for i in ids:
        df = R.frame(out[i]["rows"])
        df.to_parquet(OUT / f"B_{i}.parquet")
        trades[i] = window(tag(df, types), *TEST)
    res = evaluate(trades, ch["choice"], types, "B: 280 unseen coins")
    res["already_seen_on_unseen_coins"] = seen
    (OUT / "testB.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    show(res)


if __name__ == "__main__":
    {"fit": fit, "testA": testA, "testB": testB}[sys.argv[1]]()
