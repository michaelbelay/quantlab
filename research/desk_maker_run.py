"""15m / 30m breakout-with-flow with LIMIT entries - executes PREREGISTRATION_2026-09-28_desk_maker.md.

Signals come from desk15m_run.py unchanged (same bars, same family-B definition).
Fills and exits are walked on 1-minute bars (§5). Implicit points resolved here,
none of which loosens a gate:
  * target fills at the target price even if a 1m bar gaps through it (the
    better gap price is ignored - pessimistic); stops that gap fill at the open
  * random-entry baseline (G5): a random bar whose limit would sit on the wrong
    side of its close is skipped - that order would be marketable, i.e. taker,
    not a resting maker order
  * "missed winners" = the same exits entered at market (next 15m/30m open,
    taker + slippage) on signals whose limit never filled; reported only
  * each grid parameter has two values, so a neighbour is the other value;
    a combination passes Stage 2 when its group (direction x timeframe) passes

    .venv\\Scripts\\python.exe research\\desk_maker_run.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from desk15m_run import DEV, DEV_START, END, HOLD, SEAL_START, bars, fnum, load_coin, pf, signal  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "market" / "desk"
OUT = ROOT / "research" / "results"
PREREG = ROOT / "research" / "PREREGISTRATION_2026-09-28_desk_maker.md"
SEED = 20260929
MIN = 60 * 10**9

# §5 costs
BASE = {"maker": 0.0002, "taker": 0.0005, "slip": 0.0002}
DOUBLE = {"maker": 0.0004, "taker": 0.0010, "slip": 0.0004}
# §6 grid
TFS = {"15m": 15, "30m": 30}            # minutes per signal bar
DIRS = ["long", "short"]
ENTRIES = [{"N": n, "k": k, "E": e} for n in (20, 48) for k in (1.5, 2.5) for e in ("retest", "pullback")]
EXITS = [{"s": s, "r": r} for s in (1.0, 1.5) for r in (1.5, 2.0)]
GRID_VALUES = {"N": (20, 48), "k": (1.5, 2.5), "E": ("retest", "pullback"), "s": (1.0, 1.5), "r": (1.5, 2.0)}
T_BARS = 16                              # §5 time stop, signal bars after the fill
EXPIRY_BARS = 2                          # §5 order lifetime
PLACE_MIN = 1                            # §5 order placed 1 minute after signal close
DELAY_MIN = 15                           # §7 G7


def cid(d, tf, ep, xp):
    return "|".join(["M", d, tf] + [f"{k}={v}" for k, v in ep.items()] + [f"{k}={v}" for k, v in xp.items()])


# ------------------------------------------------------------------ 1m path walking
def walk(t, o, h, l, j, fill, sgn, dist, r, horizon, first_bar_target):
    """Walk from 1m bar j (the entry bar). Returns (exit_index, exit_raw_price, kind).

    kind: 'stop' | 'target' | 'time'. If first_bar_target is False, the entry bar
    is checked for the stop only (a limit fill and a target in the same minute
    is not credited)."""
    stop, tgt = fill - sgn * dist, fill + sgn * r * dist
    end = min(j + horizon, len(o) - 1)
    hh, ll, oo = h[j:end], l[j:end], o[j:end]
    if sgn == 1:
        hit_s = ll <= stop
        hit_t = hh > tgt
    else:
        hit_s = hh >= stop
        hit_t = ll < tgt
    if not first_bar_target and len(hit_t):
        hit_t = hit_t.copy()
        hit_t[0] = False
    js = int(np.argmax(hit_s)) if hit_s.any() else horizon
    jt = int(np.argmax(hit_t)) if hit_t.any() else horizon
    if js <= jt and js < len(hh):
        px = stop
        if js > 0 and ((sgn == 1 and oo[js] < stop) or (sgn == -1 and oo[js] > stop)):
            px = oo[js]
        return j + js, px, "stop"
    if jt < len(hh):
        return j + jt, tgt, "target"
    return end, o[end], "time"


def trade_R(entry, exit_px, kind, sgn, dist, fund, cost, maker_entry=True):
    if maker_entry:
        e_px, e_fee = entry, cost["maker"]
    else:
        e_px, e_fee = entry * (1 + sgn * cost["slip"]), cost["taker"]
    if kind == "target":
        x_px, x_fee = exit_px, cost["maker"]
    else:
        x_px, x_fee = exit_px * (1 - sgn * cost["slip"]), cost["taker"]
    pnl = sgn * (x_px - e_px) - e_fee * e_px - x_fee * x_px - sgn * fund * e_px
    return pnl / dist


def simulate(c, tf, sig_idx, d, ep, xp, place_min=PLACE_MIN, random_mode=False):
    """Limit-order simulation for one coin. Returns dict of arrays per FILLED trade
    (signal time, R base, R 2x) plus missed-signal market-entry R (base)."""
    k, t, o, h, l = c["k"][tf], c["t"], c["o"], c["h"], c["l"]
    ft, fr = c["ft"], c["fr"]
    sgn = 1 if d == "long" else -1
    tfm = TFS[tf]
    horizon = T_BARS * tfm
    ct = c["ct"][tf]
    atr, close = c["atr"][tf], c["close"][tf]
    lvl = c["hh" if sgn == 1 else "ll"][tf][ep["N"]]
    out_t, out_b, out_2, missed = [], [], [], []
    busy_until = -1
    for i in sig_idx:
        place = ct[i] + place_min * MIN
        if place < busy_until:
            continue
        a = atr[i]
        if not np.isfinite(a) or a <= 0:
            continue
        limit = lvl[i] if ep["E"] == "retest" else close[i] - sgn * 0.25 * a
        if not np.isfinite(limit):
            continue
        if random_mode and sgn * (limit - close[i]) >= 0:
            continue                                   # marketable -> not a maker order
        expiry = ct[i] + EXPIRY_BARS * tfm * MIN
        j0, j1 = np.searchsorted(t, place), np.searchsorted(t, expiry)
        if j1 <= j0 or j1 + horizon >= len(t):
            continue
        dist = xp["s"] * a
        through = (l[j0:j1] < limit) if sgn == 1 else (h[j0:j1] > limit)
        if not through.any():
            busy_until = expiry
            if not random_mode:                        # what market entry would have made
                jm = np.searchsorted(t, ct[i])
                if jm < len(t) and t[jm] == ct[i] and jm + horizon < len(t):
                    x, px, kind = walk(t, o, h, l, jm, o[jm], sgn, dist, xp["r"], horizon, True)
                    lo_, hi_ = np.searchsorted(ft, t[jm], "right"), np.searchsorted(ft, t[x], "right")
                    missed.append(trade_R(o[jm], px, kind, sgn, dist, fr[lo_:hi_].sum(), BASE, maker_entry=False))
            continue
        j = j0 + int(np.argmax(through))
        fill = min(o[j], limit) if sgn == 1 else max(o[j], limit)
        x, px, kind = walk(t, o, h, l, j, fill, sgn, dist, xp["r"], horizon, False)
        lo_, hi_ = np.searchsorted(ft, t[j], "right"), np.searchsorted(ft, t[x], "right")
        fund = fr[lo_:hi_].sum()
        out_t.append(ct[i])
        out_b.append(trade_R(fill, px, kind, sgn, dist, fund, BASE))
        out_2.append(trade_R(fill, px, kind, sgn, dist, fund, DOUBLE))
        busy_until = t[x] + MIN
    return {"t": np.array(out_t, dtype=np.int64), "rb": np.array(out_b), "r2": np.array(out_2),
            "missed": np.array(missed), "signals": len(sig_idx)}


# ------------------------------------------------------------------ data
def load(sym):
    coin = load_coin(sym)
    m1 = pd.read_parquet(DATA / sym / "klines_1m.parquet", columns=["date", "open", "high", "low"])
    c = {"t": m1["date"].values.astype("datetime64[ns]").astype(np.int64),
         "o": m1["open"].to_numpy(), "h": m1["high"].to_numpy(), "l": m1["low"].to_numpy(),
         "ft": coin["funding"]["date"].values.astype("datetime64[ns]").astype(np.int64),
         "fr": coin["funding"]["rate"].to_numpy(),
         "k": {}, "ct": {}, "atr": {}, "close": {}, "hh": {}, "ll": {}, "tt": {}, "sigs": {}}
    del m1
    for tf in TFS:
        k = bars(coin, tf)
        c["tt"][tf] = k["date"].values.astype("datetime64[ns]").astype(np.int64)
        c["ct"][tf] = k["close_time"].values.astype("datetime64[ns]").astype(np.int64)
        c["atr"][tf], c["close"][tf] = k["atr"].to_numpy(), k["close"].to_numpy()
        c["hh"][tf] = {n: k[f"hh{n}"].to_numpy() for n in (20, 48)}
        c["ll"][tf] = {n: k[f"ll{n}"].to_numpy() for n in (20, 48)}
        for d in DIRS:
            for n in (20, 48):
                for kk in (1.5, 2.5):
                    c["sigs"][(tf, d, n, kk)] = signal(k, "B", d, {"N": n, "k": kk})
        c["k"][tf] = None
    return c


# ------------------------------------------------------------------ main
def main():
    t_start = time.time()
    meta = {"prereg": PREREG.name, "prereg_sha256": hashlib.sha256(PREREG.read_bytes()).hexdigest(),
            "seed": SEED, "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    DEVP = (DEV_START.value, SEAL_START.value)
    SEALP = (SEAL_START.value, END.value)

    print("loading dev coins ...", flush=True)
    coins = {sym: load(sym) for sym in DEV}
    print(f"  ready in {time.time() - t_start:.0f}s", flush=True)

    def run(d, tf, ep, xp, pool, period, place_min=PLACE_MIN):
        res = {}
        for sym, c in pool.items():
            m = c["sigs"][(tf, d, ep["N"], ep["k"])] & (c["tt"][tf] >= period[0]) & (c["tt"][tf] < period[1])
            res[sym] = simulate(c, tf, np.flatnonzero(m), d, ep, xp, place_min)
        return res

    cat = lambda res, key: np.concatenate([v[key] for v in res.values()]) if res else np.array([])

    combos = [(d, tf, ep, xp) for d in DIRS for tf in TFS for ep in ENTRIES for xp in EXITS]
    assert len(combos) == 128, len(combos)

    # ================= Stage 1
    print("stage 1 ...", flush=True)
    s1, cache = [], {}
    for n_done, (d, tf, ep, xp) in enumerate(combos, 1):
        c_id = cid(d, tf, ep, xp)
        res = run(d, tf, ep, xp, coins, DEVP)
        cache[c_id] = res
        rb, r2, missed = cat(res, "rb"), cat(res, "r2"), cat(res, "missed")
        sigs = sum(v["signals"] for v in res.values())
        n = len(rb)
        coins_traded = sum(1 for v in res.values() if len(v["rb"]))
        coins_pos = sum(1 for v in res.values() if len(v["rb"]) and v["rb"].mean() > 0)
        row = {"id": c_id, "direction": d, "tf": tf, **ep, **xp, "signals": sigs, "trades": n,
               "fill_rate": round(n / sigs, 3) if sigs else None,
               "coins_traded": coins_traded, "coins_positive": coins_pos,
               "expectancy_R": fnum(rb.mean()) if n else None, "pf": fnum(pf(rb)) if n else None,
               "pf_2x": fnum(pf(r2)) if n else None,
               "missed_n": len(missed), "missed_market_expectancy_R": fnum(missed.mean()) if len(missed) else None,
               "per_week": round(n / ((DEVP[1] - DEVP[0]) / 6.048e14), 2)}
        fails = []
        if n < 150 or coins_traded < 10:
            fails.append("G1 trades")
        if n and pf(rb) < 1.15:
            fails.append("G2 pf")
        if not n or pf(r2) < 1.05:
            fails.append("G3 pf_2x")
        if coins_pos < 9:
            fails.append("G4 coins")
        if not fails:
            per_coin = {sym: len(v["rb"]) for sym, v in res.items() if len(v["rb"])}
            null = []
            for _ in range(200):
                rs = []
                for sym, cnt in per_coin.items():
                    c = coins[sym]
                    valid = np.flatnonzero((c["tt"][tf] >= DEVP[0]) & (c["tt"][tf] < DEVP[1]))
                    pick = np.sort(rng.choice(valid, size=min(len(valid), cnt * 6), replace=False))
                    rr = simulate(c, tf, pick, d, ep, xp, random_mode=True)["rb"]
                    rs.append(rr[:cnt])
                null.append(np.concatenate(rs).mean() if rs else 0.0)
            row["random_p95_R"] = round(float(np.percentile(null, 95)), 4)
            if not rb.mean() > row["random_p95_R"]:
                fails.append("G5 random")
        row["fails"], row["pass"] = fails, not fails
        s1.append(row)
        if n_done % 16 == 0:
            print(f"  {n_done}/128  ({time.time() - t_start:.0f}s)", flush=True)
    (OUT / "desk_maker_stage1.json").write_text(json.dumps({**meta, "rows": s1}, indent=1), encoding="utf-8")
    s1_pass = {r["id"] for r in s1 if r["pass"]}
    print(f"  stage 1: {len(s1_pass)} of 128 pass", flush=True)

    # ================= Stage 2
    print("stage 2 ...", flush=True)
    folds = []
    for i in range(6):
        tr0 = DEV_START + pd.DateOffset(months=2 * i)
        te0 = tr0 + pd.DateOffset(months=6)
        folds.append((tr0, te0, te0 + pd.DateOffset(months=2)))
    s2 = []
    for d in DIRS:
        for tf in TFS:
            fold_rows = []
            for tr0, te0, te1 in folds:
                best, best_pf = None, -1
                for ep in ENTRIES:
                    for xp in EXITS:
                        res = cache[cid(d, tf, ep, xp)]
                        r = np.concatenate([v["rb"][(v["t"] >= tr0.value) & (v["t"] < te0.value)] for v in res.values()])
                        if len(r) >= 30 and pf(r) >= 1.10 and pf(r) > best_pf:
                            best, best_pf = (ep, xp), pf(r)
                if best is None:
                    fold_rows.append({"test": f"{te0.date()}..{te1.date()}", "picked": None, "oos_R": 0.0, "oos_trades": 0})
                    continue
                res = cache[cid(d, tf, *best)]
                r = np.concatenate([v["rb"][(v["t"] >= te0.value) & (v["t"] < te1.value)] for v in res.values()])
                fold_rows.append({"test": f"{te0.date()}..{te1.date()}", "picked": cid(d, tf, *best),
                                  "train_pf": fnum(best_pf), "oos_R": round(float(r.sum()), 3), "oos_trades": len(r)})
            oos = sum(f["oos_R"] for f in fold_rows)
            pos = sum(1 for f in fold_rows if f["oos_R"] > 0)
            s2.append({"group": f"{d}|{tf}", "oos_sum_R": round(oos, 3), "folds_positive": pos,
                       "pass": oos > 0 and pos >= 4, "folds": fold_rows})
    (OUT / "desk_maker_stage2.json").write_text(json.dumps({**meta, "groups": s2}, indent=1), encoding="utf-8")
    g_pass = {g["group"]: g for g in s2 if g["pass"]}
    s2_pass = [r for r in s1 if r["pass"] and f"{r['direction']}|{r['tf']}" in g_pass]
    print(f"  stage 2: {len(g_pass)} of {len(s2)} groups pass; {len(s2_pass)} combos carry on", flush=True)

    # ================= Stage 3
    print("stage 3 ...", flush=True)
    s3 = []
    for row in s2_pass:
        d, tf = row["direction"], row["tf"]
        ep, xp = {"N": row["N"], "k": row["k"], "E": row["E"]}, {"s": row["s"], "r": row["r"]}
        fails, detail = [], {}
        for pname in ("N", "k", "E", "s", "r"):
            other = [v for v in GRID_VALUES[pname] if v != (ep | xp)[pname]][0]
            ep2, xp2 = dict(ep), dict(xp)
            (ep2 if pname in ep2 else xp2)[pname] = other
            v = pf(cat(cache[cid(d, tf, ep2, xp2)], "rb"))
            detail[f"neighbour_{pname}={other}"] = fnum(v)
            if v <= 1.0:
                fails.append(f"G6 neighbour {pname}")
        v = pf(cat(run(d, tf, ep, xp, coins, DEVP, place_min=DELAY_MIN), "rb"))
        detail["delay_15min_pf"] = fnum(v)
        if v <= 1.0:
            fails.append("G7 delay")
        res = cache[row["id"]]
        best = max(res, key=lambda s_: res[s_]["rb"].sum() if len(res[s_]["rb"]) else -1e9)
        v = pf(np.concatenate([res[s_]["rb"] for s_ in res if s_ != best]))
        detail["without_best_coin"], detail["pf_without_best_coin"] = best, fnum(v)
        if v < 1.10:
            fails.append("G8 one coin")
        s3.append({"id": row["id"], **detail, "fails": fails, "pass": not fails})
    (OUT / "desk_maker_stage3.json").write_text(json.dumps({**meta, "rows": s3}, indent=1), encoding="utf-8")
    s3_pass = [r for r in s3 if r["pass"]]
    print(f"  stage 3: {len(s3_pass)} pass", flush=True)

    # ================= Stage 4 - sealed quadrant, once
    s4 = {"opened": False, "rows": [], "untested": []}
    if s3_pass:
        rank = {r["id"]: g_pass[f"{r['direction']}|{r['tf']}"]["oos_sum_R"] for r in s2_pass}
        ordered = sorted(s3_pass, key=lambda r: -rank[r["id"]])
        chosen, s4["untested"] = ordered[:5], [r["id"] for r in ordered[5:]]
        s4["opened"] = True
        del coins
        print(f"stage 4: opening sealed quadrant for {len(chosen)} ...", flush=True)
        hold = {sym: load(sym) for sym in HOLD}
        for row in chosen:
            src = next(r for r in s1 if r["id"] == row["id"])
            d, tf = src["direction"], src["tf"]
            ep, xp = {"N": src["N"], "k": src["k"], "E": src["E"]}, {"s": src["s"], "r": src["r"]}
            res = run(d, tf, ep, xp, hold, SEALP)
            rb, r2 = cat(res, "rb"), cat(res, "r2")
            fails = []
            if len(rb) < 50:
                fails.append("G9 trades")
            if pf(rb) < 1.10:
                fails.append("G10 pf")
            if pf(r2) < 1.00:
                fails.append("G11 pf_2x")
            s4["rows"].append({"id": row["id"], "trades": len(rb), "expectancy_R": fnum(rb.mean()) if len(rb) else None,
                               "pf": fnum(pf(rb)), "pf_2x": fnum(pf(r2)), "fails": fails, "validated": not fails})
    (OUT / "desk_maker_stage4.json").write_text(json.dumps({**meta, **s4}, indent=1), encoding="utf-8")
    validated = [r["id"] for r in s4["rows"] if r["validated"]]
    print(json.dumps({"stage1_pass": len(s1_pass), "stage2_groups": len(g_pass), "stage3_pass": len(s3_pass),
                      "stage4": s4["rows"], "validated": validated,
                      "seconds": round(time.time() - t_start)}, indent=1), flush=True)


if __name__ == "__main__":
    main()
