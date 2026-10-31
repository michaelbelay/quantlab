"""Research pipeline worker (stage S4, 2026-10-04).

    .venv\\Scripts\\python.exe research\\pipeline\\run.py --batches 1 --size 24

One batch:
  1. GENERATE  `size` new candidates across families (generator.py), never a repeat.
  2. PASS 1    development coins (the 140 engine coins): base costs + 2x costs + 200 random-entry
               replicas per candidate.  -> G1 trades, G2 PF / t-stat / random baseline / deflated Sharpe.
  3. PASS 2    G2 survivors only: parameter/exit neighbours on development coins.
               -> G3 2x costs, coins profitable, single-coin share, regimes, portfolio drawdown, neighbours.
  4. DIVERSITY G3 survivors whose trades overlap > 70% with an existing survivor are near-copies.
  5. PASS 3    remaining survivors on the 280 out-of-sample coins (never used by any research).
               -> G4 out-of-sample PF / expectancy ratio / random baseline, G5 time-fold consistency.
  6. RECORD    pipeline.db + trade files; then rebuild the strategy registry.

Never touches a bot, a config or the live account. Low CPU priority; processes one coin at a
time (memory); stops cleanly between coins when research/pipeline/STOP exists.
"""
from __future__ import annotations

import argparse
import gc
import json
import sqlite3
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import psutil
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / "research" / "engine"), str(HERE)]
import backtest as BT  # noqa: E402
from backtest import Config, simulate_pair  # noqa: E402
from features import PairFeatures  # noqa: E402
import generator as GEN  # noqa: E402
import stats as ST  # noqa: E402

DB = HERE / "pipeline.db"
TRADES = HERE / "trades"
STATUS = HERE / "worker_status.json"
LOG = HERE / "worker.log"
STOPF = HERE / "STOP"
GATES = yaml.safe_load((ROOT / "research" / "registry" / "gates.yaml").read_text(encoding="utf-8"))["gates"]
FUT = ROOT / "data" / "market" / "dev_1h" / "binance" / "futures"
OOS = ROOT / "data" / "market" / "extra_coins_1h"
REGIMES = [("bull2021", "2021-01-01", "2021-11-10"), ("bear2022", "2021-11-10", "2023-01-01"),
           ("recovery2023_24", "2023-01-01", "2025-01-01"), ("recent2025_26", "2025-01-01", "2026-10-01")]
FOLDS = [(f"{y}H{h}", f"{y}-{'01' if h == 1 else '07'}-01", f"{y + (h == 2)}-{'07' if h == 1 else '01'}-01")
         for y, h in [(2022, 2), (2023, 1), (2023, 2), (2024, 1), (2024, 2), (2025, 1), (2025, 2), (2026, 1)]]
BASE_FEE, BASE_SLIP = BT.FEE, BT.SLIP
CALIBRATE = False   # --calibrate: run the live strategy's spec through the gates
FOCUS = None        # --focus: a pre-registered grid instead of the generator
VALIDATE_ALL = False  # focus yaml validate_all: every candidate goes to the unseen coins; one combined verdict
DD_PORTFOLIO = "portfolio_10"   # which portfolio construction G3 drawdown is judged on


def load_focus(path: Path):
    """Expand a pre-registered focus grid into candidates (deterministic ids)."""
    import itertools
    f = yaml.safe_load(path.read_text(encoding="utf-8"))
    global VALIDATE_ALL
    VALIDATE_ALL = bool(f.get("validate_all"))
    out = []
    if "candidates" in f:                       # explicit, frozen configurations
        for c in f["candidates"]:
            spec = {"min_score": 0.0, "regime": None, **c["spec"]}
            out.append({"id": f"focus-{f['name']}-{c['label']}", "spec": spec, "cfg": c["cfg"]})
        dd = {"p10": "portfolio_10", "p20": "portfolio_20", "live": "portfolio_live"}[f.get("drawdown_portfolio", "p10")]
        return out, dd, int(f.get("chunk", 12))
    g = f["grid"]
    for filt, reg, dirn, stop in itertools.product(g["filters"], g["regime"], g["direction"], g["stop"]):
        spec = {"family": f["family"], **f["fixed"]["spec"], "filters": filt, "regime": reg, "direction": dirn}
        cfg = {**f["fixed"]["cfg"], **stop}
        out.append({"id": f"focus-{f['name']}-{GEN.cid(spec, cfg)}", "spec": spec, "cfg": cfg})
    dd = {"p10": "portfolio_10", "p20": "portfolio_20", "live": "portfolio_live"}[f.get("drawdown_portfolio", "p10")]
    return out, dd, int(f.get("chunk", 12))
FORCE = False   # test only: push every candidate through every stage to exercise the code paths

SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (id INTEGER PRIMARY KEY, started TEXT, finished TEXT, size INTEGER,
  trials_total INTEGER, status TEXT, summary TEXT);
CREATE TABLE IF NOT EXISTS candidates (id TEXT PRIMARY KEY, batch INTEGER, family TEXT, name TEXT, spec TEXT, cfg TEXT,
  status TEXT, reason TEXT, stage TEXT, hypothesis TEXT, entry_desc TEXT, exit_desc TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS metrics (id TEXT, scope TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS gates (id TEXT, gate TEXT, result TEXT, value TEXT, threshold TEXT, detail TEXT);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(msg: str):
    line = f"{now()} {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def status(**kw):
    kw.update(pid=psutil.Process().pid, updated=now())
    STATUS.write_text(json.dumps(kw, indent=1), encoding="utf-8")


class Stop(Exception):
    pass


# ---------------------------------------------------------------- data
def dev_coins() -> list[tuple[str, Path, Path]]:
    split = json.loads((ROOT / "data" / "market" / "universe" / "split_140.json").read_text(encoding="utf-8"))
    out = []
    for c in split["dev"] + split["holdout"]:
        p = FUT / f"{c}_USDT_USDT-1h-futures.feather"
        if p.exists():
            out.append((c, p, FUT / f"{c}_USDT_USDT-1h-funding_rate.feather"))
    return out


def oos_coins() -> list[tuple[str, Path, Path]]:
    kept = json.loads((HERE / "oos_universe.json").read_text(encoding="utf-8"))["kept"]
    return [(s[:-4], OOS / s / "ohlcv_1h.feather", OOS / s / "funding.feather") for s in kept
            if (OOS / s / "ohlcv_1h.feather").exists()]


def load(path: Path, fpath: Path) -> PairFeatures | None:
    df = pd.read_feather(path)
    if len(df) < 400:
        return None
    fund = pd.read_feather(fpath) if fpath.exists() else None
    return PairFeatures(df, fund)


def mem_guard():
    for _ in range(12):
        if psutil.virtual_memory().available > 300 * 2 ** 20:
            return
        gc.collect()
        time.sleep(5)
    raise Stop("low memory (< 300 MB free for a minute)")


# ---------------------------------------------------------------- simulation passes
def to_cfg(d: dict) -> Config:
    c = Config()
    for k, v in d.items():
        setattr(c, k, tuple(v) if isinstance(v, list) else v)
    return c


def run_pass(name: str, coins, runs: list[dict], reps: int, seed: int, batch: int) -> dict:
    """runs: [{key, spec, cfg, cost_mult, random}] -> {key: {"rows": [...], "rand": array, "errors": n}}"""
    rng = np.random.default_rng(seed)
    out = {r["key"]: {"rows": [], "rand": np.zeros(reps), "errors": 0} for r in runs}
    cfgs = {r["key"]: to_cfg(r["cfg"]) for r in runs}
    t0 = time.time()
    for i, (coin, p, fp) in enumerate(coins, 1):
        if STOPF.exists():
            raise Stop("STOP file")
        mem_guard()
        try:
            f = load(p, fp)
        except Exception as e:
            log(f"  {coin}: load failed {type(e).__name__}: {e}")
            continue
        if f is None:
            continue
        dates = pd.to_datetime(f.date, utc=True)
        for r in runs:
            BT.FEE, BT.SLIP = BASE_FEE * r["cost_mult"], BASE_SLIP * r["cost_mult"]
            try:
                tr = simulate_pair(f, r["spec"], cfgs[r["key"]], coin)
            except Exception:
                out[r["key"]]["errors"] += 1
                continue
            o = out[r["key"]]
            for t in tr:
                o["rows"].append((coin, t.pnl, "long" if t.side > 0 else "short", dates[t.entry_i],
                                  dates[min(t.exit_i, len(dates) - 1)], t.bars, t.notional))
            if r["random"] and tr:
                o["rand"] += ST.random_entry_totals(rng, f.open, f.close, tr, reps, BT.FEE + BT.SLIP)
        BT.FEE, BT.SLIP = BASE_FEE, BASE_SLIP
        del f
        if i % 10 == 0:
            gc.collect()
            el = time.time() - t0
            status(state="running", batch=batch, stage=name, coin=f"{i}/{len(coins)}",
                   eta_min=round(el / i * (len(coins) - i) / 60, 1))
    return out


def frame(rows) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["pair", "pnl", "side", "entry_date", "exit_date", "bars", "notional"])


# ---------------------------------------------------------------- metrics + gates
def summarize(df: pd.DataFrame, rand: np.ndarray | None = None) -> dict:
    if df.empty:
        return {"trades": 0}
    w, l = df[df.pnl > 0].pnl.sum(), -df[df.pnl < 0].pnl.sum()
    coin = df.groupby("pair").pnl.sum()
    reg = {n: round(float(df[(df.entry_date >= pd.Timestamp(s, tz="UTC")) & (df.entry_date < pd.Timestamp(e, tz="UTC"))].pnl.sum()), 2)
           for n, s, e in REGIMES}
    port = ST.portfolio(df)
    port20 = ST.portfolio(df, slots=20)
    port_live = ST.portfolio(df, slots=20, max_same_side=10)
    m = {"trades": int(len(df)), "pf": round(float(w / l), 4) if l > 0 else None, "net": round(float(df.pnl.sum()), 2),
         "expectancy": round(float(df.pnl.mean()), 4), "win_rate": round(float((df.pnl > 0).mean() * 100), 1),
         "t_stat": ST.t_stat(df.pnl.to_numpy()), "coins": int(coin.size), "coins_profitable": int((coin > 0).sum()),
         "top_coin_share": round(float(coin.max() / coin[coin > 0].sum()), 3) if (coin > 0).any() else None,
         "regimes": reg, "portfolio_10": port, "portfolio_20": port20, "portfolio_live": port_live,
         "years": round((df.exit_date.max() - df.entry_date.min()).days / 365.25, 1),
         "long_trades": int((df.side == "long").sum()), "short_trades": int((df.side == "short").sum())}
    if rand is not None and len(rand):
        m["random_pct"] = round(float((rand < df.pnl.sum()).mean() * 100), 1)
        m["random_median"] = round(float(np.median(rand)), 2)
    sp = ST.sharpe_parts(ST.daily_series(df))
    if sp:
        m["sharpe_daily"], m["skew"], m["kurt"], m["days"] = round(sp[0], 5), round(sp[1], 3), round(sp[2], 3), sp[3]
    return m


def gate(res: list, name: str, ok, value, threshold, detail=None):
    res.append((name, "n/a" if ok is None else ("pass" if ok else "fail"), value, threshold, detail))
    return ok


# ---------------------------------------------------------------- batch
def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    return con


def family_stats(con) -> dict:
    out = {}
    for fam, n, s in con.execute("SELECT family, count(*), sum(status IN ('PROMISING','VALIDATED')) FROM candidates GROUP BY family"):
        out[fam] = (n, s or 0)
    return out


def run_batch(size: int, reps: int, seed: int):
    con = db()
    tested = {r[0] for r in con.execute("SELECT id FROM candidates")}
    batch = con.execute("INSERT INTO batches (started, size, status) VALUES (?,?,?)", (now(), size, "running")).lastrowid
    con.commit()
    cands = GEN.next_batch(size, tested, family_stats(con), seed + batch)
    if FOCUS:
        # pre-registered focused search: the next untested chunk of the fixed grid
        cands = [c for c in FOCUS if c["id"] not in tested][:size]
        if not cands:
            con.execute("DELETE FROM batches WHERE id=?", (batch,))
            con.commit()
            raise Stop("focused search complete: every configuration already tested")
    if CALIBRATE:
        # The live strategy's exact specification, run through the same gates as a new idea.
        # Shows how strict the bar is; recorded as calibration, never as a new strategy.
        spec = {"family": "volatility_breakout", "params": {"bars": 4, "atr_mult": 2.0}, "filters": ["btc_regime", "volume"],
                "trend_mode": "with", "regime": None, "direction": "both", "min_score": 0.0}
        cfg = {"leverage": 1.0, "stop_mode": "atr", "stop_atr": 2.0, "tp_mode": "none", "tp_atr": (), "tp_frac": (),
               "entry_mode": "instant", "max_bars": 400}
        cands = [{"id": "calibration-vbreak4both", "spec": spec, "cfg": cfg}]
        con.execute("DELETE FROM candidates WHERE id='calibration-vbreak4both'")
        con.execute("DELETE FROM metrics WHERE id='calibration-vbreak4both'")
        con.execute("DELETE FROM gates WHERE id='calibration-vbreak4both'")
    trials_total = GATES["G2_edge"]["trials_offset"] + len(tested - {"calibration-vbreak4both"}) + len(cands)
    log(f"batch {batch}: {len(cands)} candidates from {len({c['spec']['family'] for c in cands})} families; "
        f"trials counted for deflated Sharpe: {trials_total}")
    for c in cands:
        c["name"], c["entry"], c["exit"] = GEN.describe(c["spec"], c["cfg"])
        fn = GEN.S.FAMILIES[c["spec"]["family"]]
        c["hyp"] = (fn.__doc__ or "not recorded").strip()
        c["gates"], c["metrics"], c["status"], c["reason"], c["stage"] = [], {}, None, None, "dev"
    devc, oosc = dev_coins(), oos_coins()
    TRADES.mkdir(exist_ok=True)

    # ---- pass 1: development coins, base + 2x costs + random baseline
    runs = [{"key": (c["id"], "base"), "spec": c["spec"], "cfg": c["cfg"], "cost_mult": 1.0, "random": True} for c in cands] + \
           [{"key": (c["id"], "2x"), "spec": c["spec"], "cfg": c["cfg"], "cost_mult": 2.0, "random": False} for c in cands]
    log(f"  pass 1: {len(runs)} runs x {len(devc)} development coins")
    p1 = run_pass("pass 1 development", devc, runs, reps, seed + batch, batch)
    dev = {c["id"]: frame(p1[(c["id"], "base")]["rows"]) for c in cands}
    srs = []
    for c in cands:
        m = summarize(dev[c["id"]], p1[(c["id"], "base")]["rand"])
        m2 = summarize(frame(p1[(c["id"], "2x")]["rows"]))
        c["metrics"]["dev"], c["metrics"]["dev 2x costs"] = m, m2
        if p1[(c["id"], "base")]["errors"]:
            c["metrics"]["dev"]["errors"] = p1[(c["id"], "base")]["errors"]
        if "sharpe_daily" in m:
            srs.append(m["sharpe_daily"])
    # Variance of Sharpe across trials, pooled over every pipeline candidate tested so far plus
    # this batch. With fewer than 10 values it cannot be estimated honestly, so DSR is "n/a"
    # (a fixed guess would decide the result by itself).
    for (d,) in con.execute("SELECT data FROM metrics WHERE scope='dev' AND id != 'calibration-vbreak4both'"):
        v = json.loads(d).get("sharpe_daily")
        if v is not None:
            srs.append(v)
    sr_var = float(np.var(srs, ddof=1)) if len(srs) >= 10 else None
    G2, G3 = GATES["G2_edge"], GATES["G3_robustness"]
    survivors = []
    for c in cands:
        m, g = c["metrics"]["dev"], c["gates"]
        ok1 = gate(g, "G1 trades", m["trades"] >= GATES["G1_sanity"]["min_trades"], m["trades"], f">= {GATES['G1_sanity']['min_trades']}")
        pf, ts = m.get("pf"), m.get("t_stat")
        ok_pf = gate(g, "G2 profit factor", None if pf is None else pf >= G2["min_pf"], pf, f">= {G2['min_pf']}", "development coins")
        ok_t = gate(g, "G2 t-stat", None if ts is None else ts >= G2["min_t_stat"], None if ts is None else round(ts, 2), f">= {G2['min_t_stat']}")
        rp = m.get("random_pct")
        ok_r = gate(g, "G2 random-entry baseline", None if rp is None else rp >= G2["random_baseline_pct"], rp,
                    f">= p{G2['random_baseline_pct']}", f"{reps} replicas; median replica {m.get('random_median')}")
        dsr = None
        if "sharpe_daily" in m and sr_var is not None:
            dsr = ST.deflated_sharpe(m["sharpe_daily"], m["skew"], m["kurt"], m["days"], trials_total, sr_var)
            m["dsr"] = round(dsr, 4)
        ok_d = gate(g, "G2 deflated Sharpe", None if dsr is None else dsr >= G2["min_dsr_probability"],
                    None if dsr is None else round(dsr, 3), f">= {G2['min_dsr_probability']}",
                    (f"{trials_total} trials counted; Sharpe variance from {len(srs)} tested strategies"
                     if sr_var is not None else "not enough tested strategies (< 10) to estimate the variance")
                    + ("" if G2.get("dsr_blocking", True) else " · recorded, not blocking"))
        blocking_dsr = G2.get("dsr_blocking", True)
        fails = [n for n, r, *_ in g if r == "fail" and (blocking_dsr or n != "G2 deflated Sharpe")]
        # keep every candidate's raw development trades, including early failures
        dev[c["id"]].to_parquet(TRADES / f"{c['id']}__dev.parquet")
        if (not ok1 or not ok_pf or fails) and not FORCE:
            c["status"], c["stage"] = "REJECTED", "G2" if ok1 else "G1"
            c["reason"] = "Failed " + ", ".join(fails or ["G2 profit factor (no data)"]) + " on development coins." + \
                ("" if dsr is None or blocking_dsr else f" (DSR {dsr:.2f}, recorded only.)")
        else:
            survivors.append(c)
    log(f"  G1/G2 survivors: {len(survivors)}/{len(cands)}")

    # ---- pass 2: neighbours for G2 survivors
    if survivors:
        runs = []
        for c in survivors:
            for j, nb in enumerate(neighbours(c)):
                runs.append({"key": (c["id"], f"nb{j}"), "spec": nb[0], "cfg": nb[1], "cost_mult": 1.0, "random": False})
        log(f"  pass 2: {len(runs)} neighbour runs x {len(devc)} development coins")
        p2 = run_pass("pass 2 neighbours", devc, runs, reps, seed + batch + 1, batch)
    still = []
    for c in survivors:
        m, m2, g = c["metrics"]["dev"], c["metrics"]["dev 2x costs"], c["gates"]
        nbs = [summarize(frame(v["rows"])) for k, v in p2.items() if k[0] == c["id"]] if survivors else []
        prof = [x for x in nbs if (x.get("pf") or 0) > 1.0]
        c["metrics"]["neighbours"] = {"n": len(nbs), "profitable": len(prof), "pf": [x.get("pf") for x in nbs]}
        gate(g, "G3 2x costs", None if m2.get("pf") is None else m2["pf"] >= G3["min_pf_2x_costs"], m2.get("pf"), f">= {G3['min_pf_2x_costs']}")
        share = m["coins_profitable"] / m["coins"] if m.get("coins") else None
        gate(g, "G3 coins profitable", None if share is None else share >= G3["min_coins_profitable"],
             f"{m.get('coins_profitable')}/{m.get('coins')}", f">= {G3['min_coins_profitable']:.0%}")
        gate(g, "G3 single-coin share", None if m.get("top_coin_share") is None else m["top_coin_share"] <= G3["max_single_coin_share"],
             m.get("top_coin_share"), f"<= {G3['max_single_coin_share']}")
        pos = sum(1 for v in m["regimes"].values() if v > 0)
        gate(g, "G3 regimes positive", pos >= G3["min_regimes_positive"], f"{pos}/4", f">= {G3['min_regimes_positive']}/4", json.dumps(m["regimes"]))
        dd = m[DD_PORTFOLIO]["max_dd"]
        gate(g, "G3 portfolio drawdown", dd <= G3["max_drawdown_pct"], f"{dd}%", f"<= {G3['max_drawdown_pct']}%",
             {"portfolio_10": "10 slots, compounding", "portfolio_20": "20 slots, compounding",
              "portfolio_live": "live construction: 20 slots, <= 10 same direction"}[DD_PORTFOLIO]
             + f" · P10 {m['portfolio_10']['max_dd']}% · P20 {m['portfolio_20']['max_dd']}% · LIVE {m['portfolio_live']['max_dd']}%")
        frac = len(prof) / len(nbs) if nbs else None
        gate(g, "G3 parameter neighbours", None if frac is None else frac >= G3["min_neighbours_profitable"],
             f"{len(prof)}/{len(nbs)}", f">= {G3['min_neighbours_profitable']:.0%}")
        fails = [n for n, r, *_ in g if r == "fail" and n.startswith("G3")]
        if fails and not FORCE:
            c["status"], c["stage"], c["reason"] = "REJECTED", "G3", "Passed G1/G2; failed " + ", ".join(fails) + "."
        else:
            still.append(c)
    log(f"  G3 survivors: {len(still)}/{len(survivors)}")

    # ---- diversity
    pool = existing_survivor_keys(con)
    final = []
    for c in still:
        keys = ST.entry_keys(dev[c["id"]])
        best = max(((ST.jaccard(keys, k), n) for n, k in pool), default=(0.0, None))
        ok = gate(c["gates"], "Diversity (trade overlap)", best[0] <= GATES["diversity"]["max_overlap"], round(best[0], 3),
                  f"<= {GATES['diversity']['max_overlap']}", f"closest: {best[1]}" if best[1] else None)
        if not ok and not FORCE:
            c["status"], c["stage"], c["reason"] = "REJECTED", "diversity", f"Near-copy: {best[0]:.0%} trade overlap with {best[1]}."
        else:
            final.append(c)
            pool.append((c["id"], keys))

    # ---- pass 3: out-of-sample coins
    if VALIDATE_ALL:
        final = list(cands)          # validation run: every candidate faces the unseen coins
    if final:
        runs = [{"key": (c["id"], "oos"), "spec": c["spec"], "cfg": c["cfg"], "cost_mult": 1.0, "random": True} for c in final]
        if VALIDATE_ALL:
            runs += [{"key": (c["id"], "oos2x"), "spec": c["spec"], "cfg": c["cfg"], "cost_mult": 2.0, "random": False} for c in final]
        log(f"  pass 3: {len(runs)} runs x {len(oosc)} out-of-sample coins")
        p3 = run_pass("pass 3 out-of-sample", oosc, runs, reps, seed + batch + 2, batch)
    G4, G5 = GATES["G4_out_of_sample"], GATES["G5_walk_forward"]
    for c in final:
        oos = frame(p3[(c["id"], "oos")]["rows"])
        mo = summarize(oos, p3[(c["id"], "oos")]["rand"])
        c["metrics"]["out-of-sample"] = mo
        oos.to_parquet(TRADES / f"{c['id']}__oos.parquet")
        g, md = c["gates"], c["metrics"]["dev"]
        ok_pf = gate(g, "G4 out-of-sample PF", None if mo.get("pf") is None else mo["pf"] >= G4["min_pf"], mo.get("pf"),
                     f">= {G4['min_pf']}", f"{mo.get('coins', 0)} unseen coins, {mo.get('trades', 0)} trades")
        # Only meaningful when development expectancy is positive; a negative/negative ratio is not "kept".
        ratio = mo["expectancy"] / md["expectancy"] if mo.get("trades") and (md.get("expectancy") or 0) > 0 else None
        if ratio is None and mo.get("trades"):
            ratio = 0.0 if (md.get("expectancy") or 0) <= 0 or mo["expectancy"] <= 0 else None
        ok_ex = gate(g, "G4 expectancy kept", None if ratio is None else ratio >= G4["min_expectancy_ratio"],
                     None if ratio is None else round(ratio, 2), f">= {G4['min_expectancy_ratio']} of development")
        ok_rb = gate(g, "G4 random-entry baseline", None if mo.get("random_pct") is None else mo["random_pct"] >= GATES["G2_edge"]["random_baseline_pct"],
                     mo.get("random_pct"), f">= p{GATES['G2_edge']['random_baseline_pct']}")
        both = pd.concat([dev[c["id"]], oos], ignore_index=True)
        folds = {}
        for n, s, e in FOLDS:
            sub = both[(both.entry_date >= pd.Timestamp(s, tz="UTC")) & (both.entry_date < pd.Timestamp(e, tz="UTC"))]
            folds[n] = {"trades": int(len(sub)), "pnl": round(float(sub.pnl.sum()), 2)}
        posf = sum(1 for v in folds.values() if v["pnl"] > 0 and v["trades"] >= G5["min_trades_per_fold"])
        c["metrics"]["time folds"] = folds
        ok_wf = gate(g, "G5 time-fold consistency", posf >= G5["min_folds_positive"], f"{posf}/8",
                     f">= {G5['min_folds_positive']}/8", json.dumps(folds))
        if ok_pf and ok_ex and ok_rb and ok_wf:
            c["status"], c["stage"] = "VALIDATED", "G5"
            c["reason"] = ("Passed G1-G3 on development coins and G4/G5 on 280 coins never used by any research. "
                           "Next: forward test (G6) before it can be READY.")
        elif ok_pf and ok_ex:
            c["status"], c["stage"] = "PROMISING", "G4"
            c["reason"] = "Passed G1-G3 and the out-of-sample PF, but failed " + \
                ", ".join(n for n, r, *_ in g if r == "fail" and n.startswith(("G4", "G5"))) + "."
        else:
            c["status"], c["stage"] = "REJECTED", "G4"
            c["reason"] = "Passed G1-G3 on development coins; failed out-of-sample: " + \
                ", ".join(n for n, r, *_ in g if r == "fail" and n.startswith("G4")) + "."

    # ---- validation run: one verdict from every gate, development and unseen coins together
    if VALIDATE_ALL:
        for c in cands:
            g, mo = c["gates"], c["metrics"]["out-of-sample"]
            o2 = summarize(frame(p3[(c["id"], "oos2x")]["rows"]))
            c["metrics"]["out-of-sample 2x costs"] = o2
            gate(g, "G4 2x costs (unseen coins)", None if o2.get("pf") is None else o2["pf"] >= GATES["G3_robustness"]["min_pf_2x_costs"],
                 o2.get("pf"), f">= {GATES['G3_robustness']['min_pf_2x_costs']}")
            ddl = (mo.get("portfolio_live") or {}).get("max_dd")
            gate(g, "G4 drawdown, live construction (unseen coins)", None if ddl is None else ddl <= GATES["G3_robustness"]["max_drawdown_pct"],
                 None if ddl is None else f"{ddl}%", f"<= {GATES['G3_robustness']['max_drawdown_pct']}%",
                 f"return {(mo.get('portfolio_live') or {}).get('ret_pct')}%")
            fails = [n for n, r, *_ in g if r == "fail" and n != "G2 deflated Sharpe" and not n.startswith("Diversity")]
            oosf = [n for n in fails if n.startswith(("G4", "G5"))]
            if not fails:
                c["status"], c["stage"] = "VALIDATED", "G5"
                c["reason"] = "Validation run: passed every gate on the development coins AND on the 280 unseen coins. Next: paper forward test."
            else:
                c["status"] = "REJECTED"
                c["stage"] = "G4" if oosf else next((n.split()[0] for n in fails), "G3")
                c["reason"] = ("Validation run on the 280 unseen coins: " + (("failed " + ", ".join(oosf)) if oosf else "passed G4/G5")
                               + "; development coins: " + (", ".join(n for n in fails if n not in oosf) or "all passed") + ".")

    # ---- record
    for c in cands:
        con.execute("INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (c["id"], batch, c["spec"]["family"], c["name"], json.dumps(c["spec"]), json.dumps(c["cfg"]),
                     c["status"], c["reason"], c["stage"], c["hyp"], c["entry"], c["exit"], now()))
        for scope, m in c["metrics"].items():
            con.execute("INSERT INTO metrics VALUES (?,?,?)", (c["id"], scope, json.dumps(m, default=str)))
        for gname, r, v, th, det in c["gates"]:
            con.execute("INSERT INTO gates VALUES (?,?,?,?,?,?)", (c["id"], gname, r, None if v is None else str(v), th, det))
    counts = {s: sum(1 for c in cands if c["status"] == s) for s in ("VALIDATED", "PROMISING", "REJECTED")}
    con.execute("UPDATE batches SET finished=?, trials_total=?, status='done', summary=? WHERE id=?",
                (now(), trials_total, json.dumps(counts), batch))
    con.commit()
    con.close()
    log(f"batch {batch} done: {counts}")
    return batch, counts


def neighbours(c) -> list[tuple[dict, dict]]:
    """Up to 4 nearby variants: stop and holding period, plus one numeric family parameter."""
    spec, cfg = c["spec"], c["cfg"]
    out = []
    for k, mults in (("stop_atr", (0.75, 1.33)), ("max_bars", (0.5, 2.0))):
        for m in mults:
            nc = dict(cfg)
            nc[k] = round(cfg[k] * m, 2) if k == "stop_atr" else max(6, int(cfg[k] * m))
            out.append((spec, nc))
    num = [(k, v) for k, v in (spec.get("params") or {}).items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if num:
        k, v = num[0]
        for m in (0.8, 1.25):
            ns = json.loads(json.dumps(spec))
            ns["params"][k] = type(v)(round(v * m, 3)) if isinstance(v, float) else max(1, int(round(v * m)))
            out.append((ns, cfg))
    return out[:6]


def existing_survivor_keys(con) -> list[tuple[str, set]]:
    pool = []
    vb = ROOT / "research" / "universe_trades" / "volatility_breakout_b4~btc+vol~both__dev.parquet"
    if vb.exists():
        pool.append(("VBreak4Both", ST.entry_keys(pd.read_parquet(vb))))
    for (cid,) in con.execute("SELECT id FROM candidates WHERE status IN ('PROMISING','VALIDATED')"):
        p = TRADES / f"{cid}__dev.parquet"
        if p.exists():
            pool.append((cid, ST.entry_keys(pd.read_parquet(p))))
    return pool


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batches", type=int, default=1)
    ap.add_argument("--size", type=int, default=24)
    ap.add_argument("--reps", type=int, default=2000)   # 200 until 2026-10-09: seed noise ~1.5 pct points at p95
    ap.add_argument("--seed", type=int, default=20261004)
    ap.add_argument("--calibrate", action="store_true", help="run VBreak4Both's exact spec through every gate")
    ap.add_argument("--focus", help="pre-registered focused search (yaml in research/pipeline/focus/)")
    ap.add_argument("--test-dir", help="smoke test: write everything here, use 6 coins per set, no registry rebuild")
    a = ap.parse_args()
    global CALIBRATE, FOCUS, DD_PORTFOLIO
    CALIBRATE = a.calibrate
    if a.test_dir:
        global DB, TRADES, STATUS, LOG, STOPF, dev_coins, oos_coins
        t = Path(a.test_dir)
        t.mkdir(parents=True, exist_ok=True)
        DB, TRADES, STATUS, LOG, STOPF = t / "pipeline.db", t / "trades", t / "status.json", t / "worker.log", t / "STOP"
        _d, _o = dev_coins, oos_coins
        dev_coins, oos_coins = (lambda: _d()[:6]), (lambda: _o()[:6])
        global FORCE
        FORCE = True
    if a.focus:
        FOCUS, DD_PORTFOLIO, chunk = load_focus(Path(a.focus))
        con = db()
        done = {r[0] for r in con.execute("SELECT id FROM candidates")}
        con.close()
        left = [c for c in FOCUS if c["id"] not in done]
        a.size = chunk
        a.batches = max(1, -(-len(left) // chunk))
        log(f"focused search {Path(a.focus).name}: {len(FOCUS)} configurations, {len(left)} left, "
            f"{a.batches} batch(es) of {chunk}; drawdown judged on {DD_PORTFOLIO}")
    if a.calibrate:
        a.batches = 1
    try:
        psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    except Exception:
        pass
    if STOPF.exists():
        STOPF.unlink()
    status(state="starting", batches=a.batches)
    try:
        for i in range(a.batches):
            b, counts = run_batch(a.size, a.reps, a.seed)
            if not a.test_dir:
                status(state="rebuilding registry", batch=b, last=counts)
                subprocess.run([sys.executable, str(ROOT / "research" / "registry" / "build.py")], cwd=str(ROOT), timeout=600)
        status(state="idle", finished=now())
    except Stop as e:
        log(f"stopped: {e}")
        status(state="stopped", reason=str(e))
        con = db()
        con.execute("UPDATE batches SET status='stopped', finished=? WHERE status='running'", (now(),))
        con.commit()
        con.close()
    except Exception as e:
        log("ERROR " + traceback.format_exc())
        status(state="error", error=f"{type(e).__name__}: {e}")
        con = db()
        con.execute("UPDATE batches SET status='error', finished=? WHERE status='running'", (now(),))
        con.commit()
        con.close()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
