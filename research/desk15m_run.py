"""15m / 30m manual-signal research - executes PREREGISTRATION_2026-09-27_desk15m.md.

Every rule below is taken from that document; section numbers are cited inline.
Three points the document left implicit are resolved here and repeated in the
report (none of them loosens a gate):
  * Fees AND slippage are charged on both entry and exit, including target fills
    (a target could be a maker limit order; charging taker is the pessimistic side).
  * "Parameter neighbour" - every grid parameter has exactly two values, so the
    neighbour of a combo along a parameter is the combo with the other value.
  * Stage 2 selection is run per group (family x direction x timeframe) as the
    document states; a combination passes Stage 2 when its group passes.

    .venv\\Scripts\\python.exe research\\desk15m_run.py
"""
from __future__ import annotations

import hashlib
import itertools
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "market" / "desk"
OUT = ROOT / "research" / "results"
PREREG = ROOT / "research" / "PREREGISTRATION_2026-09-27_desk15m.md"
SEED = 20260927

# §4 splits
DEV = ["BTCUSDT", "ZECUSDT", "XRPUSDT", "NEARUSDT", "WLDUSDT", "DOGEUSDT", "UNIUSDT", "LINKUSDT",
       "ADAUSDT", "AVAXUSDT", "ONDOUSDT", "BNBUSDT", "ARBUSDT", "BCHUSDT", "DOTUSDT"]
HOLD = ["ETHUSDT", "SOLUSDT", "ENAUSDT", "SUIUSDT", "RAREUSDT", "TAOUSDT", "FILUSDT", "LTCUSDT",
        "1000PEPEUSDT", "QNTUSDT", "DASHUSDT", "ARKUSDT", "AAVEUSDT", "SAGAUSDT", "FETUSDT"]
DEV_START = pd.Timestamp("2024-09-01", tz="UTC")
SEAL_START = pd.Timestamp("2026-03-26", tz="UTC")
END = pd.Timestamp("2026-09-26", tz="UTC")

# §5 costs
BASE = {"fee": 0.0005, "slip": 0.0002}
DOUBLE = {"fee": 0.0010, "slip": 0.0004}
T_BARS = 16

# §6 grid
FAMILIES = {
    "B": [{"N": n, "k": k} for n in (20, 48) for k in (1.5, 2.5)],
    "F": [{"N": n} for n in (20, 48)],
    "P": [{"tol": t} for t in (0.001, 0.003)],
    "L": [{"m": m} for m in (2.0, 3.0)],
    "X": [{"d": d} for d in (0.10, 0.20)],
}
EXITS = [{"s": s, "r": r} for s in (1.0, 1.5) for r in (1.5, 2.0)]
TFS = ["15m", "30m"]
DIRS = ["long", "short"]
GRID_VALUES = {"N": (20, 48), "k": (1.5, 2.5), "tol": (0.001, 0.003), "m": (2.0, 3.0),
               "d": (0.10, 0.20), "s": (1.0, 1.5), "r": (1.5, 2.0)}


def cid(fam, direction, tf, ep, xp):
    parts = [fam, direction, tf] + [f"{k}={v}" for k, v in ep.items()] + [f"{k}={v}" for k, v in xp.items()]
    return "|".join(parts)


# ------------------------------------------------------------------ data + features (§3)
def load_coin(sym: str) -> dict:
    d = DATA / sym
    k = pd.read_parquet(d / "klines_15m.parquet")[["date", "open", "high", "low", "close", "volume",
                                                  "taker_buy_volume"]]
    m = pd.read_parquet(d / "metrics_5m.parquet")[["date", "oi", "top_ls_positions"]]
    f = pd.read_parquet(d / "funding.parquet")[["date", "rate"]].dropna()
    # One timestamp unit everywhere: merge_asof refuses mixed ms/ns keys under pandas 3.
    for x in (k, m, f):
        x["date"] = x["date"].astype("datetime64[ns, UTC]")

    # metrics: regular 5m grid, then lag one step - available 5 min after its timestamp (§3)
    m = m.set_index("date").sort_index()
    m = m[~m.index.duplicated()].resample("5min").last().ffill()
    m["oi_1h"] = m["oi"] / m["oi"].shift(12) - 1
    m.index = m.index + pd.Timedelta(minutes=5)
    m = m.reset_index().rename(columns={"date": "avail"})

    # funding: normalise to 8h, percentile among the trailing 30 days of settlements
    f = f.sort_values("date").reset_index(drop=True)
    gap_h = f["date"].diff().dt.total_seconds().div(3600).round()
    interval = gap_h.where(gap_h.isin([1, 2, 4, 8])).bfill().fillna(8)
    f["rate8"] = f["rate"] * 8 / interval
    t = f["date"].values.astype("datetime64[ns]").astype(np.int64)
    r8 = f["rate8"].values
    pct = np.empty(len(f))
    lo = 0
    win = 30 * 86400 * 10**9
    for i in range(len(f)):
        while t[lo] <= t[i] - win:
            lo += 1
        w = r8[lo:i + 1]
        pct[i] = (w <= r8[i]).mean()
    f["fund_pct"] = pct
    return {"k15": k, "metrics": m, "funding": f}


def bars(coin: dict, tf: str) -> pd.DataFrame:
    k = coin["k15"].copy()
    if tf == "30m":
        k = (k.set_index("date").resample("30min")
             .agg({"open": "first", "high": "max", "low": "min", "close": "last",
                   "volume": "sum", "taker_buy_volume": "sum"}).dropna().reset_index())
    step = pd.Timedelta(tf.replace("m", "min"))
    k["close_time"] = k["date"] + step
    # ATR(14), Wilder
    pc = k["close"].shift(1)
    tr = pd.concat([k["high"] - k["low"], (k["high"] - pc).abs(), (k["low"] - pc).abs()], axis=1).max(axis=1)
    k["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    k["vol_avg20"] = k["volume"].rolling(20).mean().shift(1)          # prior 20 bars
    k["buy"] = (k["taker_buy_volume"] / k["volume"]).where(k["volume"] > 0)
    k["sell"] = 1 - k["buy"]
    k["ema20"] = k["close"].ewm(span=20, adjust=False).mean()
    for n in (20, 48):
        k[f"hh{n}"] = k["high"].rolling(n).max().shift(1)
        k[f"ll{n}"] = k["low"].rolling(n).min().shift(1)
    newhigh = (k["high"] > k["hh20"]).astype(float)
    newlow = (k["low"] < k["ll20"]).astype(float)
    k["stall_up"] = newhigh.rolling(4).max() == 0      # no new 20-bar high in the last 4 bars
    k["stall_dn"] = newlow.rolling(4).max() == 0

    # 1h trend from COMPLETED 1h bars only
    h = (coin["k15"].set_index("date")["close"].resample("1h").last().dropna().to_frame())
    h["ema50"] = h["close"].ewm(span=50, adjust=False).mean()
    h["ema200"] = h["close"].ewm(span=200, adjust=False).mean()
    h["h_close_time"] = h.index + pd.Timedelta(hours=1)
    k = pd.merge_asof(k.sort_values("close_time"), h[["h_close_time", "ema50", "ema200"]].sort_values("h_close_time"),
                      left_on="close_time", right_on="h_close_time", direction="backward")

    # order flow as known at bar close
    k = pd.merge_asof(k, coin["metrics"][["avail", "oi_1h", "top_ls_positions"]], left_on="close_time",
                      right_on="avail", direction="backward")
    fu = coin["funding"][["date", "fund_pct"]].rename(columns={"date": "f_time"})
    k = pd.merge_asof(k, fu, left_on="close_time", right_on="f_time", direction="backward")
    win = {"15m": 2880, "30m": 1440}[tf]
    k["top_pct"] = k["top_ls_positions"].rolling(win, min_periods=win // 2).rank(pct=True)
    return k.reset_index(drop=True)


def signal(k: pd.DataFrame, fam: str, direction: str, p: dict) -> np.ndarray:
    L = direction == "long"
    if fam == "B":
        n, kk = p["N"], p["k"]
        vol_ok = k["volume"] >= kk * k["vol_avg20"]
        oi_up = k["oi_1h"] > 0
        s = (k["close"] > k[f"hh{n}"]) & (k["buy"] >= 0.55) if L else (k["close"] < k[f"ll{n}"]) & (k["sell"] >= 0.55)
        s = s & vol_ok & oi_up
    elif fam == "F":
        n = p["N"]
        s = ((k["low"] < k[f"ll{n}"]) & (k["close"] > k[f"ll{n}"]) & (k["sell"] >= 0.55)) if L else \
            ((k["high"] > k[f"hh{n}"]) & (k["close"] < k[f"hh{n}"]) & (k["buy"] >= 0.55))
    elif fam == "P":
        t = p["tol"]
        oi_ok = k["oi_1h"] >= -0.01
        s = ((k["ema50"] > k["ema200"]) & (k["low"] <= k["ema20"] * (1 + t)) & (k["close"] > k["ema20"])
             & (k["buy"] >= 0.52)) if L else \
            ((k["ema50"] < k["ema200"]) & (k["high"] >= k["ema20"] * (1 - t)) & (k["close"] < k["ema20"])
             & (k["sell"] >= 0.52))
        s = s & oi_ok
    elif fam == "L":
        m = p["m"]
        atr_prev = k["atr"].shift(1)
        move = (k["open"] - k["close"]) if L else (k["close"] - k["open"])
        s = (move >= m * atr_prev) & (k["volume"] >= 3 * k["vol_avg20"]) & (k["oi_1h"] <= -0.01)
    elif fam == "X":
        d = p["d"]
        s = ((k["fund_pct"] <= d) & (k["top_pct"] <= d) & k["stall_dn"]) if L else \
            ((k["fund_pct"] >= 1 - d) & (k["top_pct"] >= 1 - d) & k["stall_up"])
    else:
        raise ValueError(fam)
    return s.fillna(False).to_numpy()


# ------------------------------------------------------------------ simulation (§5)
@dataclass
class Arr:
    t: np.ndarray       # bar open time, ns
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    atr: np.ndarray
    ft: np.ndarray      # funding times ns
    fr: np.ndarray      # funding rates (raw, per settlement)


def to_arr(k: pd.DataFrame, fund: pd.DataFrame) -> Arr:
    return Arr(k["date"].values.astype("datetime64[ns]").astype(np.int64), k["open"].to_numpy(),
               k["high"].to_numpy(), k["low"].to_numpy(), k["close"].to_numpy(), k["atr"].to_numpy(),
               fund["date"].values.astype("datetime64[ns]").astype(np.int64), fund["rate"].to_numpy())


def simulate(a: Arr, idx: np.ndarray, direction: str, s: float, r: float, cost: dict, delay: int = 0):
    """Returns array of (signal_bar, R). One open trade per coin per setup."""
    sgn = 1 if direction == "long" else -1
    fee, slip = cost["fee"], cost["slip"]
    n = len(a.o)
    out_i, out_r = [], []
    busy_until = -1
    for i in idx:
        e_bar = i + 1 + delay
        if e_bar <= busy_until or e_bar + T_BARS >= n:
            continue
        atr = a.atr[i]
        if not np.isfinite(atr) or atr <= 0:
            continue
        entry = a.o[e_bar] * (1 + sgn * slip)
        dist = s * atr
        stop = entry - sgn * dist
        tgt = entry + sgn * r * dist
        seg_h = a.h[e_bar:e_bar + T_BARS]
        seg_l = a.l[e_bar:e_bar + T_BARS]
        seg_o = a.o[e_bar:e_bar + T_BARS]
        if sgn == 1:
            hit_s = seg_l <= stop
            hit_t = seg_h >= tgt
        else:
            hit_s = seg_h >= stop
            hit_t = seg_l <= tgt
        js = int(np.argmax(hit_s)) if hit_s.any() else T_BARS
        jt = int(np.argmax(hit_t)) if hit_t.any() else T_BARS
        if js <= jt and js < T_BARS:            # stop first, including same bar (pessimistic)
            j = js
            raw = stop
            # gapped through the stop: fill at the bar's open, which is worse
            if (sgn == 1 and seg_o[j] < stop) or (sgn == -1 and seg_o[j] > stop):
                raw = seg_o[j]
            x_bar = e_bar + j
        elif jt < T_BARS:
            j = jt
            raw = tgt
            if (sgn == 1 and seg_o[j] > tgt) or (sgn == -1 and seg_o[j] < tgt):
                raw = seg_o[j]
            x_bar = e_bar + j
        else:
            x_bar = e_bar + T_BARS
            raw = a.o[x_bar]
        exit_ = raw * (1 - sgn * slip)
        pnl = sgn * (exit_ - entry) - fee * (entry + exit_)
        # funding for every settlement held through: longs pay positive rates
        t0, t1 = a.t[e_bar], a.t[x_bar]
        lo, hi = np.searchsorted(a.ft, t0, "right"), np.searchsorted(a.ft, t1, "right")
        if hi > lo:
            pnl -= sgn * a.fr[lo:hi].sum() * entry
        out_i.append(i)
        out_r.append(pnl / dist)
        busy_until = x_bar
    return np.array(out_i, dtype=np.int64), np.array(out_r)


def pf(r: np.ndarray) -> float:
    g, l = r[r > 0].sum(), -r[r < 0].sum()
    return float("inf") if l == 0 and g > 0 else (float(g / l) if l > 0 else 0.0)


def fnum(x):
    return None if x is None else (round(x, 4) if np.isfinite(x) else "inf")


# ------------------------------------------------------------------ main
def main():
    t_start = time.time()
    prereg_hash = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    meta = {"prereg": PREREG.name, "prereg_sha256": prereg_hash, "seed": SEED,
            "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}

    # ---- build features once per coin/tf; keep only what simulation needs
    print("loading + features ...", flush=True)
    feats = {}   # (sym, tf) -> (Arr, time Series ns, signals dict cid_entry -> bool array)
    for sym in DEV + HOLD:
        coin = load_coin(sym)
        for tf in TFS:
            k = bars(coin, tf)
            sigs = {}
            for fam, eps in FAMILIES.items():
                for ep in eps:
                    for d in DIRS:
                        sigs[(fam, d, json.dumps(ep, sort_keys=True))] = signal(k, fam, d, ep)
            feats[(sym, tf)] = (to_arr(k, coin["funding"]), k["date"].values.astype("datetime64[ns]").astype(np.int64), sigs)
        del coin
    print(f"  features ready in {time.time() - t_start:.0f}s", flush=True)

    ns = lambda ts: ts.value
    DEVP = (ns(DEV_START), ns(SEAL_START))
    SEALP = (ns(SEAL_START), ns(END))

    def run(fam, d, tf, ep, xp, coins, period, cost=BASE, delay=0):
        """Trades per coin: {sym: (signal_times_ns, R)}"""
        res = {}
        for sym in coins:
            a, tt, sigs = feats[(sym, tf)]
            m = sigs[(fam, d, json.dumps(ep, sort_keys=True))] & (tt >= period[0]) & (tt < period[1])
            ii, rr = simulate(a, np.flatnonzero(m), d, xp["s"], xp["r"], cost, delay)
            res[sym] = (tt[ii] if len(ii) else np.array([], dtype=np.int64), rr)
        return res

    allr = lambda res: np.concatenate([v[1] for v in res.values()]) if res else np.array([])

    combos = [(fam, d, tf, ep, xp) for fam, eps in FAMILIES.items() for ep in eps
              for d in DIRS for tf in TFS for xp in EXITS]
    assert len(combos) == 192, len(combos)

    # ================= Stage 1 (§7) - dev coins x dev period
    print("stage 1 ...", flush=True)
    s1 = []
    base_cache = {}
    for fam, d, tf, ep, xp in combos:
        c = cid(fam, d, tf, ep, xp)
        res = run(fam, d, tf, ep, xp, DEV, DEVP)
        base_cache[c] = res
        r = allr(res)
        n = len(r)
        coins_traded = sum(1 for v in res.values() if len(v[1]))
        coins_pos = sum(1 for v in res.values() if len(v[1]) and v[1].mean() > 0)
        row = {"id": c, "family": fam, "direction": d, "tf": tf, **ep, **xp, "trades": n,
               "coins_traded": coins_traded, "coins_positive": coins_pos,
               "expectancy_R": fnum(r.mean()) if n else None, "pf": fnum(pf(r)) if n else None,
               "per_week": round(n / ((DEVP[1] - DEVP[0]) / 6.048e14), 2)}
        fails = []
        if n < 150 or coins_traded < 10:
            fails.append("G1 trades")
        if n and pf(r) < 1.15:
            fails.append("G2 pf")
        r2 = allr(run(fam, d, tf, ep, xp, DEV, DEVP, DOUBLE))      # reported for every combo
        row["pf_2x"] = fnum(pf(r2)) if len(r2) else None
        if not len(r2) or pf(r2) < 1.05:
            fails.append("G3 pf_2x")
        if coins_pos < 9:
            fails.append("G4 coins")
        # G5 only where it can still matter (G1-G4 passed) - it is expensive
        if not fails:
            per_coin = {sym: len(v[1]) for sym, v in res.items()}
            null = []
            for _ in range(200):
                rs = []
                for sym, cnt in per_coin.items():
                    if not cnt:
                        continue
                    a, tt, _s = feats[(sym, tf)]
                    valid = np.flatnonzero((tt >= DEVP[0]) & (tt < DEVP[1]))
                    pick = np.sort(rng.choice(valid, size=min(len(valid), int(cnt * 1.6)), replace=False))
                    _, rr = simulate(a, pick, d, xp["s"], xp["r"], BASE)
                    rs.append(rr[:cnt] if len(rr) >= cnt else rr)
                null.append(np.concatenate(rs).mean() if rs else 0.0)
            p95 = float(np.percentile(null, 95))
            row["random_p95_R"] = round(p95, 4)
            if not r.mean() > p95:
                fails.append("G5 random")
        row["fails"] = fails
        row["pass"] = not fails
        s1.append(row)
    (OUT / "desk15m_stage1.json").write_text(json.dumps({**meta, "rows": s1}, indent=1), encoding="utf-8")
    s1_pass = {r["id"] for r in s1 if r["pass"]}
    print(f"  stage 1: {len(s1_pass)} of 192 pass", flush=True)

    # ================= Stage 2 (§7) - walk-forward per group, dev coins inside dev period
    print("stage 2 ...", flush=True)
    folds = []
    for i in range(6):
        tr0 = DEV_START + pd.DateOffset(months=2 * i)
        te0 = tr0 + pd.DateOffset(months=6)
        te1 = te0 + pd.DateOffset(months=2)
        folds.append((tr0, te0, te1))
    groups = {}
    for fam, d, tf, ep, xp in combos:
        groups.setdefault((fam, d, tf), []).append((ep, xp))
    s2 = []
    for (fam, d, tf), members in groups.items():
        fold_rows = []
        for tr0, te0, te1 in folds:
            best, best_pf = None, -1
            for ep, xp in members:
                res = base_cache[cid(fam, d, tf, ep, xp)]
                r = np.concatenate([v[1][(v[0] >= tr0.value) & (v[0] < te0.value)] for v in res.values()])
                if len(r) >= 30 and pf(r) >= 1.10 and pf(r) > best_pf:
                    best, best_pf = (ep, xp), pf(r)
            if best is None:
                fold_rows.append({"test": f"{te0.date()}..{te1.date()}", "picked": None, "oos_R": 0.0, "oos_trades": 0})
                continue
            res = base_cache[cid(fam, d, tf, *best)]
            r = np.concatenate([v[1][(v[0] >= te0.value) & (v[0] < te1.value)] for v in res.values()])
            fold_rows.append({"test": f"{te0.date()}..{te1.date()}", "picked": cid(fam, d, tf, *best),
                              "train_pf": fnum(best_pf), "oos_R": round(float(r.sum()), 3), "oos_trades": len(r)})
        oos = sum(f["oos_R"] for f in fold_rows)
        pos = sum(1 for f in fold_rows if f["oos_R"] > 0)
        s2.append({"group": f"{fam}|{d}|{tf}", "oos_sum_R": round(oos, 3), "folds_positive": pos,
                   "pass": oos > 0 and pos >= 4, "folds": fold_rows})
    (OUT / "desk15m_stage2.json").write_text(json.dumps({**meta, "groups": s2}, indent=1), encoding="utf-8")
    g_pass = {g["group"]: g for g in s2 if g["pass"]}
    s2_pass = [r for r in s1 if r["pass"] and f"{r['family']}|{r['direction']}|{r['tf']}" in g_pass]
    print(f"  stage 2: {len(g_pass)} of {len(s2)} groups pass; {len(s2_pass)} combos carry on", flush=True)

    # ================= Stage 3 (§7) - robustness
    print("stage 3 ...", flush=True)
    s3 = []
    for row in s2_pass:
        fam, d, tf = row["family"], row["direction"], row["tf"]
        ep = {k: row[k] for k in FAMILIES[fam][0]}
        xp = {"s": row["s"], "r": row["r"]}
        fails, detail = [], {}
        # G6 neighbours
        for pname in list(ep) + ["s", "r"]:
            other = [v for v in GRID_VALUES[pname] if v != (ep | xp)[pname]][0]
            ep2, xp2 = dict(ep), dict(xp)
            (ep2 if pname in ep2 else xp2)[pname] = other
            nres = base_cache.get(cid(fam, d, tf, ep2, xp2)) or run(fam, d, tf, ep2, xp2, DEV, DEVP)
            v = pf(allr(nres))
            detail[f"neighbour_{pname}={other}"] = fnum(v)
            if v <= 1.0:
                fails.append(f"G6 neighbour {pname}")
        # G7 human delay
        v = pf(allr(run(fam, d, tf, ep, xp, DEV, DEVP, BASE, delay=1)))
        detail["delay_1bar_pf"] = fnum(v)
        if v <= 1.0:
            fails.append("G7 delay")
        # G8 not one coin
        res = base_cache[row["id"]]
        best = max(res, key=lambda s_: res[s_][1].sum() if len(res[s_][1]) else -1e9)
        v = pf(np.concatenate([res[s_][1] for s_ in res if s_ != best]))
        detail["without_best_coin"] = best
        detail["pf_without_best_coin"] = fnum(v)
        if v < 1.10:
            fails.append("G8 one coin")
        s3.append({"id": row["id"], **detail, "fails": fails, "pass": not fails})
    (OUT / "desk15m_stage3.json").write_text(json.dumps({**meta, "rows": s3}, indent=1), encoding="utf-8")
    s3_pass = [r for r in s3 if r["pass"]]
    print(f"  stage 3: {len(s3_pass)} pass", flush=True)

    # ================= Stage 4 (§7) - sealed quadrant, once, at most 5
    s4 = {"opened": False, "rows": [], "untested": []}
    if s3_pass:
        rank = {r["id"]: g_pass[f"{r['family']}|{r['direction']}|{r['tf']}"]["oos_sum_R"] for r in s2_pass}
        ordered = sorted(s3_pass, key=lambda r: -rank[r["id"]])
        chosen, s4["untested"] = ordered[:5], [r["id"] for r in ordered[5:]]
        s4["opened"] = True
        print(f"stage 4: opening sealed quadrant for {len(chosen)} ...", flush=True)
        for row in chosen:
            fam, d, tf = row["id"].split("|")[:3]
            src = next(r for r in s1 if r["id"] == row["id"])
            ep = {k: src[k] for k in FAMILIES[fam][0]}
            xp = {"s": src["s"], "r": src["r"]}
            r = allr(run(fam, d, tf, ep, xp, HOLD, SEALP))
            r2 = allr(run(fam, d, tf, ep, xp, HOLD, SEALP, DOUBLE))
            fails = []
            if len(r) < 50:
                fails.append("G9 trades")
            if pf(r) < 1.10:
                fails.append("G10 pf")
            if pf(r2) < 1.00:
                fails.append("G11 pf_2x")
            s4["rows"].append({"id": row["id"], "trades": len(r), "expectancy_R": fnum(r.mean()) if len(r) else None,
                               "pf": fnum(pf(r)), "pf_2x": fnum(pf(r2)), "fails": fails, "validated": not fails})
    (OUT / "desk15m_stage4.json").write_text(json.dumps({**meta, **s4}, indent=1), encoding="utf-8")
    validated = [r["id"] for r in s4["rows"] if r["validated"]]
    print(json.dumps({"stage1_pass": len(s1_pass), "stage2_groups": len(g_pass), "stage3_pass": len(s3_pass),
                      "stage4": s4["rows"], "validated": validated,
                      "seconds": round(time.time() - t_start)}, indent=1), flush=True)


if __name__ == "__main__":
    main()
