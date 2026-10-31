"""1h / 4h breakout-with-flow research - executes PREREGISTRATION_2026-09-28_desk1h4h.md.

Built on desk15m_run.py (same data loading, costs, funding, pessimistic fills and
gate logic). What differs, each from the pre-registration:
  * signals on 1h / 4h bars resampled from 15m, aligned to UTC hours (§3)
  * open-interest change measured over the signal bar: 1h or 4h (§6, Flow 3)
  * entry at the open of the 15m bar starting when the signal bar closes, and the
    exit path walked on 15m bars; stop and target touched in one 15m bar = stop (§5)
  * time stop 24 bars on 1h, 12 bars on 4h, exiting at the next 15m open (§6)
  * gate thresholds per timeframe (§7); human delay = 30 minutes (§7 G7)
  * control grid without the flow filters, reported only (§6)
Implicit points resolved the same way as the 15m/30m run (none loosens a gate):
  * fees and slippage charged on both sides, including target fills
  * each grid parameter has two values, so a neighbour is the other value
  * a combination passes Stage 2 when its group (direction x timeframe) passes

    .venv\\Scripts\\python.exe research\\desk1h4h_run.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from desk15m_run import (BASE, DEV, DEV_START, DOUBLE, END, HOLD, SEAL_START,  # noqa: E402
                         fnum, load_coin, pf)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "research" / "results"
PREREG = ROOT / "research" / "PREREGISTRATION_2026-09-28_desk1h4h.md"
SEED = 20260928

TFS = ["1h", "4h"]
DIRS = ["long", "short"]
Q = {"1h": 4, "4h": 16}                  # 15m bars per signal bar
T_HTF = {"1h": 24, "4h": 12}             # §6 time stop, in signal bars
ENTRIES = [{"N": n, "k": k} for n in (20, 48) for k in (1.5, 2.5)]
EXITS = [{"s": s, "r": r} for s in (1.0, 1.5) for r in (1.5, 2.0)]
GRID_VALUES = {"N": (20, 48), "k": (1.5, 2.5), "s": (1.0, 1.5), "r": (1.5, 2.0)}
# §7 per-timeframe minimums
G1_MIN = {"1h": 150, "4h": 60}
WF_MIN = {"1h": 30, "4h": 12}
G9_MIN = {"1h": 50, "4h": 20}
DELAY_15M = 2                            # §7 G7: 30 minutes late


def cid(kind, d, tf, ep, xp):
    return "|".join([kind, d, tf] + [f"{k}={v}" for k, v in ep.items()] + [f"{k}={v}" for k, v in xp.items()])


# ------------------------------------------------------------------ features (§3, §6)
def htf_bars(coin: dict, tf: str) -> pd.DataFrame:
    k = (coin["k15"].set_index("date").resample(tf)
         .agg({"open": "first", "high": "max", "low": "min", "close": "last",
               "volume": "sum", "taker_buy_volume": "sum"}).dropna().reset_index())
    k["close_time"] = k["date"] + pd.Timedelta(tf)
    pc = k["close"].shift(1)
    tr = pd.concat([k["high"] - k["low"], (k["high"] - pc).abs(), (k["low"] - pc).abs()], axis=1).max(axis=1)
    k["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    k["vol_avg20"] = k["volume"].rolling(20).mean().shift(1)
    k["buy"] = (k["taker_buy_volume"] / k["volume"]).where(k["volume"] > 0)
    k["sell"] = 1 - k["buy"]
    for n in (20, 48):
        k[f"hh{n}"] = k["high"].rolling(n).max().shift(1)
        k[f"ll{n}"] = k["low"].rolling(n).min().shift(1)
    # OI change over the signal bar, from the lagged 5-min series (§3: available 5 min late)
    m = coin["metrics"][["avail", "oi"]].copy()
    m["oi_bar"] = m["oi"] / m["oi"].shift(12 * Q[tf] // 4) - 1
    k = pd.merge_asof(k.sort_values("close_time"), m[["avail", "oi_bar"]], left_on="close_time",
                      right_on="avail", direction="backward")
    return k.reset_index(drop=True)


def signal(k: pd.DataFrame, d: str, p: dict, flow: bool) -> np.ndarray:
    n = p["N"]
    s = (k["close"] > k[f"hh{n}"]) if d == "long" else (k["close"] < k[f"ll{n}"])
    if flow:
        share = k["buy"] if d == "long" else k["sell"]
        s = s & (k["volume"] >= p["k"] * k["vol_avg20"]) & (share >= 0.55) & (k["oi_bar"] > 0)
    return s.fillna(False).to_numpy()


# ------------------------------------------------------------------ simulation (§5), on 15m bars
@dataclass
class A15:
    t: np.ndarray
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    ft: np.ndarray
    fr: np.ndarray


def simulate(a: A15, e_idx: np.ndarray, atr: np.ndarray, d: str, s: float, r: float, cost: dict, T: int):
    """e_idx: 15m entry bar per signal (-1 = no such bar). Returns (signal positions, R)."""
    sgn = 1 if d == "long" else -1
    fee, slip = cost["fee"], cost["slip"]
    n = len(a.o)
    out_i, out_r = [], []
    busy_until = -1
    for pos in range(len(e_idx)):
        e = e_idx[pos]
        if e < 0 or e <= busy_until or e + T >= n:
            continue
        v = atr[pos]
        if not np.isfinite(v) or v <= 0:
            continue
        entry = a.o[e] * (1 + sgn * slip)
        dist = s * v
        stop, tgt = entry - sgn * dist, entry + sgn * r * dist
        sh, sl, so = a.h[e:e + T], a.l[e:e + T], a.o[e:e + T]
        hit_s = sl <= stop if sgn == 1 else sh >= stop
        hit_t = sh >= tgt if sgn == 1 else sl <= tgt
        js = int(np.argmax(hit_s)) if hit_s.any() else T
        jt = int(np.argmax(hit_t)) if hit_t.any() else T
        if js <= jt and js < T:
            j, raw = js, stop
            if (sgn == 1 and so[j] < stop) or (sgn == -1 and so[j] > stop):
                raw = so[j]
            x = e + j
        elif jt < T:
            j, raw = jt, tgt
            if (sgn == 1 and so[j] > tgt) or (sgn == -1 and so[j] < tgt):
                raw = so[j]
            x = e + j
        else:
            x = e + T
            raw = a.o[x]
        ex = raw * (1 - sgn * slip)
        pnl = sgn * (ex - entry) - fee * (entry + ex)
        lo, hi = np.searchsorted(a.ft, a.t[e], "right"), np.searchsorted(a.ft, a.t[x], "right")
        if hi > lo:
            pnl -= sgn * a.fr[lo:hi].sum() * entry
        out_i.append(pos)
        out_r.append(pnl / dist)
        busy_until = x
    return np.array(out_i, dtype=np.int64), np.array(out_r)


# ------------------------------------------------------------------ main
def main():
    t_start = time.time()
    meta = {"prereg": PREREG.name, "prereg_sha256": hashlib.sha256(PREREG.read_bytes()).hexdigest(),
            "seed": SEED, "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    print("loading + features ...", flush=True)
    feats = {}   # (sym, tf) -> dict
    for sym in DEV + HOLD:
        coin = load_coin(sym)
        k15 = coin["k15"]
        a = A15(k15["date"].values.astype("datetime64[ns]").astype(np.int64), k15["open"].to_numpy(),
                k15["high"].to_numpy(), k15["low"].to_numpy(),
                coin["funding"]["date"].values.astype("datetime64[ns]").astype(np.int64),
                coin["funding"]["rate"].to_numpy())
        for tf in TFS:
            k = htf_bars(coin, tf)
            ct = k["close_time"].values.astype("datetime64[ns]").astype(np.int64)
            ent = {}
            for delay in (0, DELAY_15M):
                want = ct + delay * 15 * 60 * 10**9
                j = np.searchsorted(a.t, want)
                ok = (j < len(a.t)) & (a.t[np.minimum(j, len(a.t) - 1)] == want)
                ent[delay] = np.where(ok, j, -1)
            sigs = {}
            for d in DIRS:
                for ep in ENTRIES:
                    sigs[("B", d, json.dumps(ep))] = signal(k, d, ep, True)
                    sigs[("C", d, json.dumps(ep))] = signal(k, d, ep, False)
            feats[(sym, tf)] = {"a": a, "tt": k["date"].values.astype("datetime64[ns]").astype(np.int64),
                                "atr": k["atr"].to_numpy(), "ent": ent, "sigs": sigs}
        del coin
    print(f"  features ready in {time.time() - t_start:.0f}s", flush=True)

    DEVP = (DEV_START.value, SEAL_START.value)
    SEALP = (SEAL_START.value, END.value)

    def run(kind, d, tf, ep, xp, coins, period, cost=BASE, delay=0):
        res = {}
        for sym in coins:
            f = feats[(sym, tf)]
            m = f["sigs"][(kind, d, json.dumps(ep))] & (f["tt"] >= period[0]) & (f["tt"] < period[1])
            idx = np.flatnonzero(m)
            ii, rr = simulate(f["a"], f["ent"][delay][idx], f["atr"][idx], d, xp["s"], xp["r"], cost,
                              T_HTF[tf] * Q[tf])
            res[sym] = (f["tt"][idx[ii]] if len(ii) else np.array([], dtype=np.int64), rr)
        return res

    allr = lambda res: np.concatenate([v[1] for v in res.values()]) if res else np.array([])

    def stats(res, r):
        n = len(r)
        return {"trades": n, "coins_traded": sum(1 for v in res.values() if len(v[1])),
                "coins_positive": sum(1 for v in res.values() if len(v[1]) and v[1].mean() > 0),
                "expectancy_R": fnum(r.mean()) if n else None, "pf": fnum(pf(r)) if n else None,
                "per_week": round(n / ((DEVP[1] - DEVP[0]) / 6.048e14), 2)}

    combos = [(d, tf, ep, xp) for d in DIRS for tf in TFS for ep in ENTRIES for xp in EXITS]
    assert len(combos) == 64, len(combos)

    # ================= control (§6) - reported, never a candidate
    ctrl = []
    for d, tf, ep, xp in combos:
        res = run("C", d, tf, ep, xp, DEV, DEVP)
        r = allr(res)
        r2 = allr(run("C", d, tf, ep, xp, DEV, DEVP, DOUBLE))
        ctrl.append({"id": cid("C", d, tf, ep, xp), **stats(res, r), "pf_2x": fnum(pf(r2)) if len(r2) else None})
    (OUT / "desk1h4h_control.json").write_text(json.dumps({**meta, "rows": ctrl}, indent=1), encoding="utf-8")

    # ================= Stage 1 (§7)
    print("stage 1 ...", flush=True)
    s1, cache = [], {}
    for d, tf, ep, xp in combos:
        c = cid("B", d, tf, ep, xp)
        res = run("B", d, tf, ep, xp, DEV, DEVP)
        cache[c] = res
        r = allr(res)
        row = {"id": c, "direction": d, "tf": tf, **ep, **xp, **stats(res, r)}
        fails = []
        if row["trades"] < G1_MIN[tf] or row["coins_traded"] < 10:
            fails.append("G1 trades")
        if row["trades"] and pf(r) < 1.15:
            fails.append("G2 pf")
        r2 = allr(run("B", d, tf, ep, xp, DEV, DEVP, DOUBLE))
        row["pf_2x"] = fnum(pf(r2)) if len(r2) else None
        if not len(r2) or pf(r2) < 1.05:
            fails.append("G3 pf_2x")
        if row["coins_positive"] < 9:
            fails.append("G4 coins")
        if not fails:
            per_coin = {sym: len(v[1]) for sym, v in res.items() if len(v[1])}
            null = []
            for _ in range(200):
                rs = []
                for sym, cnt in per_coin.items():
                    f = feats[(sym, tf)]
                    valid = np.flatnonzero((f["tt"] >= DEVP[0]) & (f["tt"] < DEVP[1]))
                    pick = np.sort(rng.choice(valid, size=min(len(valid), int(cnt * 1.6)), replace=False))
                    _, rr = simulate(f["a"], f["ent"][0][pick], f["atr"][pick], d, xp["s"], xp["r"], BASE,
                                     T_HTF[tf] * Q[tf])
                    rs.append(rr[:cnt])
                null.append(np.concatenate(rs).mean() if rs else 0.0)
            row["random_p95_R"] = round(float(np.percentile(null, 95)), 4)
            if not r.mean() > row["random_p95_R"]:
                fails.append("G5 random")
        row["fails"], row["pass"] = fails, not fails
        s1.append(row)
    (OUT / "desk1h4h_stage1.json").write_text(json.dumps({**meta, "rows": s1}, indent=1), encoding="utf-8")
    s1_pass = {r["id"] for r in s1 if r["pass"]}
    print(f"  stage 1: {len(s1_pass)} of 64 pass", flush=True)

    # ================= Stage 2 (§7) - walk-forward per direction x timeframe
    print("stage 2 ...", flush=True)
    folds = []
    for i in range(6):
        tr0 = DEV_START + pd.DateOffset(months=2 * i)
        te0 = tr0 + pd.DateOffset(months=6)
        folds.append((tr0, te0, te0 + pd.DateOffset(months=2)))
    s2 = []
    for d in DIRS:
        for tf in TFS:
            members = [(ep, xp) for ep in ENTRIES for xp in EXITS]
            fold_rows = []
            for tr0, te0, te1 in folds:
                best, best_pf = None, -1
                for ep, xp in members:
                    res = cache[cid("B", d, tf, ep, xp)]
                    r = np.concatenate([v[1][(v[0] >= tr0.value) & (v[0] < te0.value)] for v in res.values()])
                    if len(r) >= WF_MIN[tf] and pf(r) >= 1.10 and pf(r) > best_pf:
                        best, best_pf = (ep, xp), pf(r)
                if best is None:
                    fold_rows.append({"test": f"{te0.date()}..{te1.date()}", "picked": None, "oos_R": 0.0,
                                      "oos_trades": 0})
                    continue
                res = cache[cid("B", d, tf, *best)]
                r = np.concatenate([v[1][(v[0] >= te0.value) & (v[0] < te1.value)] for v in res.values()])
                fold_rows.append({"test": f"{te0.date()}..{te1.date()}", "picked": cid("B", d, tf, *best),
                                  "train_pf": fnum(best_pf), "oos_R": round(float(r.sum()), 3),
                                  "oos_trades": len(r)})
            oos = sum(f["oos_R"] for f in fold_rows)
            pos = sum(1 for f in fold_rows if f["oos_R"] > 0)
            s2.append({"group": f"{d}|{tf}", "oos_sum_R": round(oos, 3), "folds_positive": pos,
                       "pass": oos > 0 and pos >= 4, "folds": fold_rows})
    (OUT / "desk1h4h_stage2.json").write_text(json.dumps({**meta, "groups": s2}, indent=1), encoding="utf-8")
    g_pass = {g["group"]: g for g in s2 if g["pass"]}
    s2_pass = [r for r in s1 if r["pass"] and f"{r['direction']}|{r['tf']}" in g_pass]
    print(f"  stage 2: {len(g_pass)} of {len(s2)} groups pass; {len(s2_pass)} combos carry on", flush=True)

    # ================= Stage 3 (§7) - robustness
    print("stage 3 ...", flush=True)
    s3 = []
    for row in s2_pass:
        d, tf = row["direction"], row["tf"]
        ep, xp = {"N": row["N"], "k": row["k"]}, {"s": row["s"], "r": row["r"]}
        fails, detail = [], {}
        for pname in ("N", "k", "s", "r"):
            other = [v for v in GRID_VALUES[pname] if v != (ep | xp)[pname]][0]
            ep2, xp2 = dict(ep), dict(xp)
            (ep2 if pname in ep2 else xp2)[pname] = other
            v = pf(allr(cache[cid("B", d, tf, ep2, xp2)]))
            detail[f"neighbour_{pname}={other}"] = fnum(v)
            if v <= 1.0:
                fails.append(f"G6 neighbour {pname}")
        v = pf(allr(run("B", d, tf, ep, xp, DEV, DEVP, BASE, delay=DELAY_15M)))
        detail["delay_30min_pf"] = fnum(v)
        if v <= 1.0:
            fails.append("G7 delay")
        res = cache[row["id"]]
        best = max(res, key=lambda s_: res[s_][1].sum() if len(res[s_][1]) else -1e9)
        v = pf(np.concatenate([res[s_][1] for s_ in res if s_ != best]))
        detail["without_best_coin"], detail["pf_without_best_coin"] = best, fnum(v)
        if v < 1.10:
            fails.append("G8 one coin")
        s3.append({"id": row["id"], **detail, "fails": fails, "pass": not fails})
    (OUT / "desk1h4h_stage3.json").write_text(json.dumps({**meta, "rows": s3}, indent=1), encoding="utf-8")
    s3_pass = [r for r in s3 if r["pass"]]
    print(f"  stage 3: {len(s3_pass)} pass", flush=True)

    # ================= Stage 4 (§7) - sealed quadrant, once, at most 5
    s4 = {"opened": False, "rows": [], "untested": []}
    if s3_pass:
        rank = {r["id"]: g_pass[f"{r['direction']}|{r['tf']}"]["oos_sum_R"] for r in s2_pass}
        ordered = sorted(s3_pass, key=lambda r: -rank[r["id"]])
        chosen, s4["untested"] = ordered[:5], [r["id"] for r in ordered[5:]]
        s4["opened"] = True
        print(f"stage 4: opening sealed quadrant for {len(chosen)} ...", flush=True)
        for row in chosen:
            src = next(r for r in s1 if r["id"] == row["id"])
            d, tf = src["direction"], src["tf"]
            ep, xp = {"N": src["N"], "k": src["k"]}, {"s": src["s"], "r": src["r"]}
            r = allr(run("B", d, tf, ep, xp, HOLD, SEALP))
            r2 = allr(run("B", d, tf, ep, xp, HOLD, SEALP, DOUBLE))
            fails = []
            if len(r) < G9_MIN[tf]:
                fails.append("G9 trades")
            if pf(r) < 1.10:
                fails.append("G10 pf")
            if pf(r2) < 1.00:
                fails.append("G11 pf_2x")
            s4["rows"].append({"id": row["id"], "trades": len(r), "expectancy_R": fnum(r.mean()) if len(r) else None,
                               "pf": fnum(pf(r)), "pf_2x": fnum(pf(r2)), "fails": fails, "validated": not fails})
    (OUT / "desk1h4h_stage4.json").write_text(json.dumps({**meta, **s4}, indent=1), encoding="utf-8")
    validated = [r["id"] for r in s4["rows"] if r["validated"]]
    print(json.dumps({"stage1_pass": len(s1_pass), "stage2_groups": len(g_pass), "stage3_pass": len(s3_pass),
                      "stage4": s4["rows"], "validated": validated,
                      "seconds": round(time.time() - t_start)}, indent=1), flush=True)


if __name__ == "__main__":
    main()
