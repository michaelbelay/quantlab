"""Weekly relative-strength rotation - executes PREREGISTRATION_2026-09-28_rotation.md (LOCKED).

Offline research only: reads data/market/rotation (Binance public archive).
Touches no bot, config, strategy, credential or account.

Start-up refuses to run unless every constant in THRESH matches the table in
§9.1 of the pre-registration (operator AND value).

Points the document left implicit, resolved here and repeated in the report
(none of them loosens a gate):
  * BTC's 200-day EMA is warmed on 2020 daily closes (archive 1d file), so the
    regime filter is defined from the first week instead of guessing early on.
  * Each period (dev / sealed) is simulated from an empty book; walk-forward
    folds are slices of the one continuous dev-period run.
  * Sharpe and CAGR use every week of the period, cash weeks included (return 0).
  * Walk-forward benchmark (H-LO extra condition): eligibility uses the picked
    variant's lookback in each fold, and L=28 in folds that hold cash.
  * A position whose data stops mid-week pays the exit cost that same week and is
    not carried; the 3% haircut applies in the unfavourable direction.
  * Sealed period count is whatever whole weeks fit before the data end
    (execution Monday + 7 days <= 2026-09-25 23:00).

    .venv\\Scripts\\python.exe research\\rotation_run.py
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "market" / "rotation"
OUT = ROOT / "research" / "results"
PREREG = ROOT / "research" / "PREREGISTRATION_2026-09-28_rotation.md"
PREREG_SHA = "1bd2aee3759fbbf8057bdbb60f879465d96b223946ebe89fea999a9336a0df6d"
# Amendment v3 (LOCKED 2026-09-29): A1 zero-volume = missing, A2 >=7 d = stopped,
# A3 no 90-symbol check, A6 crypto-only universe, A7 audit-only mode.
AMEND = ROOT / "research" / "AMENDMENT_2026-09-29_rotation_v3.md"
AMEND_SHA = "58d236807d6445044cac900a3375c1d44d2b49c9231a9dd79e24a013492a2004"
SNAPSHOT = DATA / "exchangeinfo_2026-09-29.json"
SNAPSHOT_SHA = "a808644abb3c2c31f452c4c7db4a08350265b2c5f537ade40d91a142f19fd502"
NONCOIN_FIRST_BAR = pd.Timestamp("2025-08-06 09:00", tz="UTC")     # A6 rule 3
STOP_GAP = pd.Timedelta(hours=168)                                  # A2

# ------------------------------------------------------------------ §9.1 thresholds
THRESH = {
    "G1_WEEKS": (">=", 150), "G2_SHARPE": (">=", 0.80), "G3_SHARPE_2X": (">=", 0.60),
    "LO_CAGR_EDGE": (">=", 5.0), "LO_SHARPE_EDGE": (">=", 0.30),
    "LS_CAGR": (">", 0.0), "LS_SHARPE": (">=", 0.80), "LS_MAXDD": ("<=", 35.0), "LS_ABS_CORR": ("<=", 0.50),
    "G5_PCTL": (">", 95), "G5_RUNS": ("", 200), "G6_MAXDD": ("<=", 50.0), "G7_REGIMES": (">=", 3),
    "WF_G1_WEEKS": (">=", 40), "WF_SHARPE": (">=", 0.50), "WF_SHARPE_2X": (">=", 0.40), "WF_FOLDS_POS": (">=", 5),
    "G8_SHARPE": (">=", 0.40), "G9_SHARPE": (">=", 0.50), "G10_SHARPE": (">=", 0.60),
    "G11_SHARPE": (">=", 0.60), "G12_SHARPE_2X": (">=", 0.40),
    "G13_LO_SHARPE_EDGE": (">=", 0.20), "G13_LS_SHARPE": (">=", 0.60), "G13_LS_MAXDD": ("<=", 35.0),
    "G13_LS_ABS_CORR": ("<=", 0.50), "G14_RET_2X": (">", 0.0),
    "MIN_ELIGIBLE": (">=", 15), "TOP_VOLUME": ("", 40), "MIN_AGE_DAYS": ("", 60),
    "FEE": ("", 0.05), "SLIP": ("", 0.05), "DELIST_HAIRCUT": ("", 3.0), "SEED": ("", 20260930),
}


def check_thresholds() -> str:
    text = PREREG.read_text(encoding="utf-8")
    sec = text.split("### 9.1", 1)[1].split("## 10.", 1)[0]
    found = {}
    for line in sec.splitlines():
        m = re.match(r"^\|\s*([A-Z0-9_]+)\s*\|.*\|\s*(>=|<=|>|<)?\s*([0-9.]+)\s*\|\s*$", line)
        if m:
            found[m.group(1)] = (m.group(2) or "", float(m.group(3)))
    bad = []
    for k, (op, v) in THRESH.items():
        if k not in found:
            bad.append(f"{k}: missing from pre-registration")
        elif found[k][0] != op or abs(found[k][1] - float(v)) > 1e-12:
            bad.append(f"{k}: code {op}{v} vs pre-registration {found[k][0]}{found[k][1]}")
    for k in found:
        if k not in THRESH:
            bad.append(f"{k}: in pre-registration, not in code")
    if bad:
        raise SystemExit("THRESHOLD MISMATCH - refusing to run:\n  " + "\n  ".join(bad))
    return f"{len(found)} thresholds match §9.1"


def ok(x: float, key: str) -> bool:
    op, v = THRESH[key]
    return {">=": x >= v, "<=": x <= v, ">": x > v, "<": x < v}[op]


T = {k: v[1] for k, v in THRESH.items()}
FEE, SLIP, HAIR = T["FEE"] / 100, T["SLIP"] / 100, T["DELIST_HAIRCUT"] / 100
H = pd.Timedelta(hours=1)
DEV_START, SEAL_START = pd.Timestamp("2021-01-01", tz="UTC"), pd.Timestamp("2026-03-26", tz="UTC")
DATA_END = pd.Timestamp("2026-09-25 23:00", tz="UTC")
REGIMES = {"bull2021": ("2021-01-01", "2022-01-01"), "bear2022": ("2022-01-01", "2023-01-01"),
           "recovery2023_24": ("2023-01-01", "2025-01-01"), "recent2025_26": ("2025-01-01", "2026-03-26")}
FOLDS = [(f"{y}-{m:02d}-01", f"{y + (m == 7)}-{(m + 6 - 1) % 12 + 1:02d}-01") for y in (2022, 2023, 2024, 2025)
         for m in (1, 7)]
VARIANTS = [{"L": L, "K": K, "filt": f} for L in (14, 28) for K in (3, 5) for f in (False, True)]
HYPS = ["LO", "LS"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_documents() -> dict:
    got = {"prereg": sha(PREREG), "amendment": sha(AMEND), "exchangeinfo_snapshot": sha(SNAPSHOT)}
    want = {"prereg": PREREG_SHA, "amendment": AMEND_SHA, "exchangeinfo_snapshot": SNAPSHOT_SHA}
    bad = [f"{k}: {got[k]} != locked {want[k]}" for k in got if got[k] != want[k]]
    if bad:
        raise SystemExit("DOCUMENT HASH MISMATCH - refusing to run:\n  " + "\n  ".join(bad))
    return got


def classify(syms: list[str]) -> tuple[list[str], dict]:
    """A6: crypto iff snapshot underlyingType == COIN; absent from the snapshot -> crypto iff the
    first archive bar is before the first non-COIN bar. Returns (crypto symbols, excluded by class)."""
    info = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    ut = {s["symbol"]: s.get("underlyingType") for s in info["symbols"]}
    keep, excluded = [], {}
    for s in syms:
        if s in ut:
            if ut[s] == "COIN":
                keep.append(s)
            else:
                excluded.setdefault(str(ut[s]), []).append(s)
            continue
        k = pd.read_parquet(DATA / s / "klines_1h.parquet")
        first = k["date"].iloc[0] if len(k) and "date" in k else None
        if first is None or first < NONCOIN_FIRST_BAR:
            keep.append(s)                 # absent + pre-TradFi (or no bars at all: inert)
        else:
            excluded.setdefault("UNCLASSIFIABLE", []).append(s)
    return keep, excluded


def universe_of(sym: str) -> str:
    return "dev" if int(hashlib.sha256(sym.encode()).hexdigest(), 16) % 2 == 0 else "holdout"


# ------------------------------------------------------------------ data
def weeks() -> pd.DatetimeIndex:
    return pd.date_range("2021-01-04", "2026-09-21", freq="7D", tz="UTC")   # Mondays 00:00


def btc_filter(W: pd.DatetimeIndex, btc_hourly: pd.DataFrame) -> np.ndarray:
    """True = long leg allowed (BTC daily close >= its 200-day EMA at ranking time)."""
    cache = DATA / "BTCUSDT_1d_2020.parquet"
    if not cache.exists():
        rows = []
        for m in range(1, 13):
            url = f"https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-2020-{m:02d}.zip"
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                df = pd.read_csv(z.open(z.namelist()[0]), header=None, dtype=str)
            if str(df.iat[0, 0]).strip() == "open_time":
                df = df.iloc[1:]
            rows.append(pd.DataFrame({"date": pd.to_datetime(pd.to_numeric(df[0]), unit="ms", utc=True),
                                      "close": pd.to_numeric(df[4])}))
        pd.concat(rows).to_parquet(cache, index=False)
    d20 = pd.read_parquet(cache)
    s20 = pd.Series(d20["close"].to_numpy(), index=d20["date"] + pd.Timedelta(days=1))  # close known at next 00:00
    hc = pd.Series(btc_hourly["close"].to_numpy(), index=btc_hourly["date"] + H)
    s21 = hc[hc.index.hour == 0]
    daily = pd.concat([s20, s21]).sort_index()
    daily = daily[~daily.index.duplicated(keep="last")]
    ema = daily.ewm(span=200, adjust=False).mean()
    c, e = daily.reindex(W), ema.reindex(W)
    return (c >= e).fillna(False).to_numpy()


def load_instruments(W: pd.DatetimeIndex, syms: list[str]):
    nW = len(W)
    cols = {k: [] for k in ("rc0", "rc14", "rc28", "ent_mon", "ext_mon", "dl_mon", "fund_mon", "ent_tue", "ext_tue",
                            "dl_tue", "fund_tue", "age_ok", "act7", "qv30", "gap14", "gap28")}
    meta, audit = [], []
    btc = None
    Wn = W.values.astype("datetime64[ns]").astype(np.int64)
    for sym in syms:
        kp = DATA / sym / "klines_1h.parquet"
        if not kp.exists():
            audit.append({"symbol": sym, "status": "no file"})
            continue
        k = pd.read_parquet(kp)
        if not len(k) or "volume" not in k:
            audit.append({"symbol": sym, "status": "no bars in window"})
            continue
        zero_bars = int((k["volume"] == 0).sum())
        k = k[k["volume"] > 0].reset_index(drop=True)          # A1: zero-volume bars are missing bars
        if not len(k):
            audit.append({"symbol": sym, "status": "no traded bars in window", "zero_volume_bars_dropped": zero_bars})
            continue
        if sym == "BTCUSDT":
            btc = k
        f = pd.read_parquet(DATA / sym / "funding.parquet")
        ft = f["date"].values.astype("datetime64[ns]").astype(np.int64)
        fr = f["rate"].to_numpy()
        dt = k["date"]
        notrade = dt.diff() - H                                  # hours with no traded bar
        seg = (notrade >= STOP_GAP).cumsum().to_numpy()         # A2: >= 7 days = stopped, new instrument
        a_rec = {"symbol": sym, "universe": universe_of(sym), "first": str(dt.iloc[0]), "last_traded": str(dt.iloc[-1]),
                 "bars": len(k), "zero_volume_bars_dropped": zero_bars,
                 "zero_volume_bars_remaining": int((k["volume"] == 0).sum()), "segments": int(seg.max()) + 1,
                 "segment_starts": [str(x) for x in dt[notrade >= STOP_GAP]],
                 "gaps_24h_7d": int(((notrade > pd.Timedelta(hours=24)) & (notrade < STOP_GAP)).sum()),
                 "funding_rows": len(f), "dead": bool(dt.iloc[-1] < DATA_END - pd.Timedelta(days=2))}
        audit.append(a_rec)
        for s in np.unique(seg):
            h = k[seg == s].reset_index(drop=True)
            hd = h["date"]
            t = hd.values.astype("datetime64[ns]").astype(np.int64)
            o, c = h["open"].to_numpy(), h["close"].to_numpy()
            close_ct = pd.Series(c, index=hd + H)
            open_s = pd.Series(o, index=hd)
            rc0 = close_ct.reindex(W).to_numpy()
            rc14 = close_ct.reindex(W - pd.Timedelta(days=14)).to_numpy()
            rc28 = close_ct.reindex(W - pd.Timedelta(days=28)).to_numpy()
            seg_start = hd.iloc[0]
            age_ok = np.asarray((W - seg_start) >= pd.Timedelta(days=T["MIN_AGE_DAYS"]), dtype=bool)
            day = h.set_index("date")[["volume", "quote_volume"]].resample("1D").sum()
            full = pd.date_range(day.index[0], day.index[-1], freq="1D")
            day = day.reindex(full, fill_value=0.0)
            act = (day["volume"] > 0).astype(float).rolling(7).sum() == 7
            qv = day["quote_volume"].rolling(30, min_periods=1).sum()
            prev_day = W - pd.Timedelta(days=1)
            act7 = act.reindex(prev_day).fillna(False).to_numpy().astype(bool)
            qv30 = qv.reindex(prev_day).fillna(0.0).to_numpy()
            gends = hd[(hd.diff() - H) > pd.Timedelta(hours=24)].values.astype("datetime64[ns]").astype(np.int64)
            gapok = {}
            for L in (14, 28):
                okL = np.ones(nW, dtype=bool)
                for g in gends:
                    okL &= ~((g > Wn - L * 86400 * 10**9) & (g <= Wn))
                gapok[L] = okL

            def legs(entry_off, hold):
                ent = open_s.reindex(W + entry_off).to_numpy()
                targ = (W + entry_off + hold).values.astype("datetime64[ns]").astype(np.int64)
                j = np.searchsorted(t, targ)
                ext = np.full(nW, np.nan)
                dl = np.zeros(nW, dtype=bool)
                x_t = np.zeros(nW, dtype=np.int64)
                inside = j < len(t)
                ext[inside] = o[j[inside]]
                x_t[inside] = t[j[inside]]
                dl[~inside] = True
                ext[~inside] = c[-1]
                x_t[~inside] = t[-1] + 3600 * 10**9
                e_t = (W + entry_off).values.astype("datetime64[ns]").astype(np.int64)
                lo = np.searchsorted(ft, e_t, "right")
                hi = np.searchsorted(ft, x_t, "right")
                cs = np.concatenate([[0.0], np.cumsum(fr)])
                fund = cs[hi] - cs[lo]
                return ent, ext, dl, fund
            em, xm, dm, fm = legs(H, pd.Timedelta(days=7))
            et, xt, dtu, fu = legs(pd.Timedelta(days=1), pd.Timedelta(days=7))
            for key, arr in (("rc0", rc0), ("rc14", rc14), ("rc28", rc28), ("ent_mon", em), ("ext_mon", xm),
                             ("dl_mon", dm), ("fund_mon", fm), ("ent_tue", et), ("ext_tue", xt), ("dl_tue", dtu),
                             ("fund_tue", fu), ("age_ok", age_ok), ("act7", act7), ("qv30", qv30),
                             ("gap14", gapok[14]), ("gap28", gapok[28])):
                cols[key].append(arr)
            meta.append({"symbol": sym, "universe": universe_of(sym), "segment": int(s)})
    A = {k: np.vstack(v) for k, v in cols.items()}
    return A, meta, audit, btc


# ------------------------------------------------------------------ simulation (§5, §7)
class Sim:
    def __init__(self, A, meta, W, btc_ok):
        self.A, self.meta, self.W, self.btc_ok = A, meta, W, btc_ok
        self.sym = np.array([m["symbol"] for m in meta])
        self.uni = np.array([m["universe"] for m in meta])
        self._elig = {}

    def eligible(self, universe, L, w, exclude=None):
        key = (universe, L, w, exclude)
        if key in self._elig:
            return self._elig[key]
        A = self.A
        m = ((self.uni == universe) & A["age_ok"][:, w] & A["act7"][:, w] & A[f"gap{L}"][:, w]
             & np.isfinite(A["rc0"][:, w]) & np.isfinite(A[f"rc{L}"][:, w]))
        if exclude is not None:
            m &= self.sym != exclude
        idx = np.flatnonzero(m)
        idx = idx[np.argsort(-A["qv30"][idx, w], kind="stable")][: T["TOP_VOLUME"]]
        self._elig[key] = idx
        return idx

    def run(self, universe, weeks_idx, hyp, v, exec_="mon", rng=None, exclude=None, log=None):
        """Returns (net base, net 2x, gross exposure, contributions by symbol)."""
        A, L, K = self.A, v["L"], v["K"]
        ent, ext, dl, fund = A[f"ent_{exec_}"], A[f"ext_{exec_}"], A[f"dl_{exec_}"], A[f"fund_{exec_}"]
        prev = {}                       # instrument -> drifted signed weight
        rb, r2, gross, turns = [], [], [], []
        contrib = {}
        for w in weeks_idx:
            E = self.eligible(universe, L, w, exclude)
            tgt = {}
            if len(E) >= T["MIN_ELIGIBLE"]:
                if hyp == "BENCH":
                    cand = [i for i in E if np.isfinite(ent[i, w])]
                    for i in cand:
                        tgt[i] = 1.0 / len(cand)
                    if log is not None:
                        log["subs"] += len(E) - len(cand)
                else:
                    if rng is None:
                        score = A["rc0"][E, w] / A[f"rc{L}"][E, w] - 1
                        order = E[np.lexsort((-A["qv30"][E, w], -score))]
                    else:
                        order = rng.permutation(E)
                    longs, shorts = [], []
                    long_on = not (v["filt"] and not self.btc_ok[w])
                    if long_on:
                        for i in order:
                            if len(longs) == K:
                                break
                            if np.isfinite(ent[i, w]):
                                longs.append(i)
                            elif log is not None:
                                log["subs"] += 1
                    if hyp == "LS":
                        # bottom K, disjoint from the long leg (or from the would-be top K when the
                        # filter has the long leg flat - the short leg itself is unaffected)
                        top_set = set(longs) if long_on else set(order[:K].tolist())
                        for i in order[::-1]:
                            if len(shorts) == K:
                                break
                            if i in top_set:
                                continue
                            if np.isfinite(ent[i, w]):
                                shorts.append(i)
                            elif log is not None:
                                log["subs"] += 1
                    wl = (1.0 / K) if hyp == "LO" else (0.5 / K)
                    for i in longs:
                        tgt[i] = wl
                    for i in shorts:
                        tgt[i] = -0.5 / K
            keys = set(tgt) | set(prev)
            turnover = sum(abs(tgt.get(i, 0.0) - prev.get(i, 0.0)) for i in keys)
            gret, fcost, dl_turn, new_prev = 0.0, 0.0, 0.0, {}
            for i, wi in tgt.items():
                p = ext[i, w] / ent[i, w] - 1
                if dl[i, w]:
                    p = (ext[i, w] * (1 - HAIR if wi > 0 else 1 + HAIR)) / ent[i, w] - 1
                    dl_turn += abs(wi * (1 + p))
                    if log is not None:
                        log["delist"].append({"week": str(self.W[w].date()), "symbol": self.sym[i],
                                              "side": "long" if wi > 0 else "short", "ret": round(float(p), 4)})
                else:
                    new_prev[i] = wi * (1 + p)
                gret += wi * p
                fcost += wi * fund[i, w]
                contrib[self.sym[i]] = contrib.get(self.sym[i], 0.0) + wi * p
            turns.append(turnover + dl_turn)
            base = (FEE + SLIP) * (turnover + dl_turn)
            rb.append(gret - fcost - base)
            r2.append(gret - fcost - 2 * base)
            gross.append(sum(abs(x) for x in tgt.values()))
            eq = 1 + gret
            prev = {i: x / eq for i, x in new_prev.items()} if eq > 0 else {}
        self.last_turnover = np.array(turns)     # weekly traded weight, for the §8 tie-break
        return np.array(rb), np.array(r2), np.array(gross), contrib


# ------------------------------------------------------------------ metrics
def metrics(r: np.ndarray, gross: np.ndarray | None = None) -> dict:
    n = len(r)
    if n == 0:
        return {"weeks": 0}
    sd = r.std(ddof=1) if n > 1 else 0.0
    eq = np.cumprod(1 + r)
    dd = 1 - eq / np.maximum.accumulate(np.concatenate([[1.0], eq]))[1:]
    return {"weeks": n, "traded_weeks": int((gross > 0).sum()) if gross is not None else None,
            "mean_week": float(r.mean()), "sharpe": float(r.mean() / sd * np.sqrt(52)) if sd > 0 else 0.0,
            "cagr_pct": float((eq[-1] ** (52 / n) - 1) * 100) if eq[-1] > 0 else -100.0,
            "total_pct": float((eq[-1] - 1) * 100), "maxdd_pct": float(dd.max() * 100)}


def rnd(d):
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}


def beats(hyp, m, b, rs, rb_, prefix=""):
    """§7.2 at base costs. Returns list of failed sub-conditions."""
    f = []
    if hyp == "LO":
        if not ok(m["cagr_pct"] - b["cagr_pct"], "LO_CAGR_EDGE"):
            f.append("cagr_edge")
        if not ok(m["sharpe"] - b["sharpe"], "LO_SHARPE_EDGE"):
            f.append("sharpe_edge")
        if not m["maxdd_pct"] <= b["maxdd_pct"]:
            f.append("dd_vs_market")
    else:
        corr = float(np.corrcoef(rs, rb_)[0, 1]) if np.std(rs) > 0 and np.std(rb_) > 0 else 0.0
        if not ok(m["cagr_pct"], "LS_CAGR"):
            f.append("cagr")
        if not ok(m["sharpe"], "LS_SHARPE"):
            f.append("sharpe")
        if not ok(m["maxdd_pct"], "LS_MAXDD"):
            f.append("maxdd")
        if not ok(abs(corr), "LS_ABS_CORR"):
            f.append("corr")
    return [prefix + x for x in f]


def vid(hyp, v):
    return f"{hyp}|L={v['L']}|K={v['K']}|filt={'on' if v['filt'] else 'off'}"


def select(rows):
    """§8 step 3: highest Sharpe at 2x; tie -> lower turnover, shorter L, smaller K."""
    if not rows:
        return None
    return sorted(rows, key=lambda r: (-round(r["sharpe_2x"], 10), r["turnover"], r["L"], r["K"]))[0]


# ------------------------------------------------------------------ main
RELAUNCHES = ["AERGOUSDT", "AIAUSDT", "BNXUSDT", "CTKUSDT", "CVCUSDT", "CVXUSDT", "ICPUSDT", "LITUSDT",
              "MAVIAUSDT", "PUMPUSDT", "SLPUSDT", "TLMUSDT"]          # amendment A4, "7+ days, resumed"


def final_audit(W, syms, excluded, A, meta, audit, docs, meta0) -> dict:
    """Amendment A7. Dates, counts and eligibility only - no returns, no strategy, no benchmark."""
    a2 = json.loads((OUT / "rotation_audit2.json").read_text(encoding="utf-8"))
    a2sym = {x["symbol"]: x for x in a2["symbols"]}
    by = {a["symbol"]: a for a in audit}
    crit = {}
    crit["1_thresholds_match"] = True                            # check_thresholds() already raised otherwise
    crit["2_document_hashes"] = docs["prereg"] == PREREG_SHA and docs["amendment"] == AMEND_SHA
    info = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    ut = {s["symbol"]: s.get("underlyingType") for s in info["symbols"]}
    noncrypto_in = [s for s in syms if s in ut and ut[s] != "COIN"]
    crit["3_universe_crypto_only_679"] = not noncrypto_in and len(syms) == 679
    zero_left = sum(a.get("zero_volume_bars_remaining", 0) for a in audit)
    crit["4_zero_volume_bars_remaining_0"] = zero_left == 0
    dead_now = sorted(a["symbol"] for a in audit if a.get("dead"))
    dead_a2 = sorted(s for s in syms if a2sym.get(s, {}).get("dead"))
    lt_mismatch = [s for s in syms if s in by and "last_traded" in by[s] and a2sym.get(s, {}).get("last_traded")
                   and pd.Timestamp(by[s]["last_traded"]) != pd.Timestamp(a2sym[s]["last_traded"])]
    crit["5_dead_end_at_last_traded"] = dead_now == dead_a2 and not lt_mismatch
    ex88 = [s for s in syms if a2sym.get(s, {}).get("existed_at_2021_01")]
    cov = [s for s in ex88 if s in by and by[s].get("first") and by[s]["first"] < "2021-02-01"]
    crit["6_coverage_85_of_88"] = (len(cov), len(ex88)) == (85, 88)
    rel = {s: {"segments": by.get(s, {}).get("segments"), "new_instrument_starts": by.get(s, {}).get("segment_starts")}
           for s in RELAUNCHES}
    crit["7_relaunches_split"] = all(s in syms and (rel[s]["segments"] or 0) >= 2 for s in RELAUNCHES)

    # information, not gates: instruments and weekly eligible counts
    S0 = Sim(A, meta, W, np.zeros(len(W), dtype=bool))
    elig = {}
    for u in ("dev", "holdout"):
        for L in (14, 28):
            cnt = np.array([len(S0.eligible(u, L, w)) for w in range(len(W))])
            thin = [str(W[w].date()) for w in range(len(W)) if cnt[w] < T["MIN_ELIGIBLE"]]
            elig[f"{u}|L={L}"] = {"min": int(cnt.min()), "median": float(np.median(cnt)), "max": int(cnt.max()),
                                  "weeks_below_15": len(thin), "weeks_below_15_list": thin}
    res = {**meta0, "documents_sha256": docs, "pass": all(crit.values()), "criteria": crit,
           "universe": {"archive_symbols": len(syms) + sum(len(v) for v in excluded.values()),
                        "crypto": len(syms), "excluded_by_class": {k: len(v) for k, v in excluded.items()},
                        "excluded_symbols": excluded, "noncrypto_found_in_universe": noncrypto_in},
           "instruments": {"total": len(meta), "dev": sum(1 for m in meta if m["universe"] == "dev"),
                           "holdout": sum(1 for m in meta if m["universe"] == "holdout")},
           "zero_volume_bars_dropped": sum(a.get("zero_volume_bars_dropped", 0) for a in audit),
           "zero_volume_bars_remaining": zero_left,
           "dead": {"count": len(dead_now), "audit2_restricted_to_crypto": len(dead_a2),
                    "only_here": sorted(set(dead_now) - set(dead_a2)), "only_audit2": sorted(set(dead_a2) - set(dead_now)),
                    "last_traded_mismatches": lt_mismatch},
           "coverage_2021_01": {"existed": len(ex88), "covered": len(cov),
                                "not_covered": sorted(set(ex88) - set(cov))},
           "relaunches": rel, "eligible_per_week": elig,
           "symbols_without_traded_bars": [a["symbol"] for a in audit if a.get("status")],
           "symbols_detail": audit}
    (OUT / "rotation_final_audit.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    return res


def main():
    t0 = time.time()
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ("--audit-only", "--run"):
        raise SystemExit("usage: rotation_run.py --audit-only | --run   (A7: results only after a passing audit)")
    print(check_thresholds(), flush=True)
    docs = check_documents()
    print(f"documents verified: prereg {docs['prereg'][:8]}, amendment {docs['amendment'][:8]}, "
          f"exchangeInfo snapshot {docs['exchangeinfo_snapshot'][:8]}", flush=True)
    meta0 = {"prereg": PREREG.name, "prereg_sha256": docs["prereg"], "amendment": AMEND.name,
             "amendment_sha256": docs["amendment"], "exchangeinfo_snapshot_sha256": docs["exchangeinfo_snapshot"],
             "seed": T["SEED"], "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    OUT.mkdir(parents=True, exist_ok=True)
    W = weeks()
    all_syms = json.loads((DATA / "symbols.json").read_text(encoding="utf-8"))["symbols"]
    syms, excluded = classify(all_syms)
    print(f"A6 universe: {len(syms)} crypto of {len(all_syms)}; excluded {({k: len(v) for k, v in excluded.items()})}",
          flush=True)
    print("loading instruments ...", flush=True)
    A, meta, audit, btc = load_instruments(W, syms)

    fa = final_audit(W, syms, excluded, A, meta, audit, docs, meta0)
    print(json.dumps({"pass": fa["pass"], "criteria": fa["criteria"], "universe": {k: v for k, v in fa["universe"].items()
                      if k != "excluded_symbols"}, "instruments": fa["instruments"], "dead": fa["dead"],
                      "coverage_2021_01": fa["coverage_2021_01"],
                      "zero_volume_bars": [fa["zero_volume_bars_dropped"], fa["zero_volume_bars_remaining"]],
                      "eligible_per_week": {k: {x: v[x] for x in ("min", "median", "max", "weeks_below_15")}
                                            for k, v in fa["eligible_per_week"].items()}},
                     indent=1, default=str), flush=True)
    print(f"final audit {'PASSED' if fa['pass'] else 'FAILED'} ({time.time() - t0:.0f}s)", flush=True)
    if not fa["pass"]:
        raise SystemExit("A7: final audit failed - nothing further runs")
    if mode == "--audit-only":
        return
    if btc is None:
        raise SystemExit("BTCUSDT missing - regime filter undefined")

    btc_ok = btc_filter(W, btc)
    S = Sim(A, meta, W, btc_ok)
    Wd = np.array([x for x in range(len(W)) if W[x] < SEAL_START and W[x] + pd.Timedelta(days=8) <= DATA_END])
    Ws = np.array([x for x in range(len(W)) if W[x] >= SEAL_START and W[x] + pd.Timedelta(days=7, hours=1) <= DATA_END])
    wk = lambda idx, a, b: np.array([k for k, x in enumerate(idx) if pd.Timestamp(a, tz="UTC") <= W[x] < pd.Timestamp(b, tz="UTC")])
    print(f"  dev weeks {len(Wd)}, sealed weeks {len(Ws)}", flush=True)

    bench = {}
    for L in (14, 28):
        b1, b2, bg, _ = S.run("dev", Wd, "BENCH", {"L": L, "K": 0, "filt": False})
        bench[L] = (b1, b2, bg)

    results = {"meta": meta0, "hypotheses": {}}
    for hyp in HYPS:
        print(f"== {hyp} ==", flush=True)
        # ---------------- Stage 1
        rows, series = [], {}
        for v in VARIANTS:
            log = {"subs": 0, "delist": []}
            rb, r2, g, contrib = S.run("dev", Wd, hyp, v, log=log)
            series[vid(hyp, v)] = (rb, r2, g, contrib, S.last_turnover)
            m, m2 = metrics(rb, g), metrics(r2, g)
            b = metrics(bench[v["L"]][0])
            reg = {name: float(np.prod(1 + rb[wk(Wd, a, bb)]) - 1) * 100 for name, (a, bb) in REGIMES.items()}
            fails = []
            if not ok(m["traded_weeks"], "G1_WEEKS"):
                fails.append("G1 weeks")
            if not ok(m["sharpe"], "G2_SHARPE"):
                fails.append("G2 sharpe")
            if not ok(m2["sharpe"], "G3_SHARPE_2X"):
                fails.append("G3 sharpe_2x")
            fails += ["G4 " + x for x in beats(hyp, m, b, rb, bench[v["L"]][0])]
            if not ok(m["maxdd_pct"], "G6_MAXDD"):
                fails.append("G6 maxdd")
            if not ok(sum(1 for x in reg.values() if x > 0), "G7_REGIMES"):
                fails.append("G7 regimes")
            turn = float(S.last_turnover.mean()) if len(g) else 0.0
            rows.append({"id": vid(hyp, v), **v, **rnd(m), "sharpe_2x": round(m2["sharpe"], 4),
                         "cagr_2x_pct": round(m2["cagr_pct"], 4), "benchmark": rnd(b),
                         "regimes_pct": {k_: round(x, 2) for k_, x in reg.items()},
                         "substitutions": log["subs"], "delist_events": log["delist"],
                         "turnover": turn, "fails": fails})
            print(f"  {vid(hyp, v)}: sharpe {m['sharpe']:.2f} (2x {m2['sharpe']:.2f}) cagr {m['cagr_pct']:.1f}% "
                  f"dd {m['maxdd_pct']:.1f}% | bench sharpe {b['sharpe']:.2f} cagr {b['cagr_pct']:.1f}% dd {b['maxdd_pct']:.1f}% "
                  f"| fails {fails}", flush=True)
        cand = select([r for r in rows if not r["fails"]])
        hres = {"stage1": rows, "candidate": cand["id"] if cand else None}
        # G5 selection-aware random
        if cand:
            rng = np.random.default_rng(T["SEED"])
            null = []
            for run_i in range(T["G5_RUNS"]):
                null.append(max(S.run("dev", Wd, hyp, v, rng=rng)[0].mean() for v in VARIANTS))
            p = float(np.percentile(null, T["G5_PCTL"]))
            cand["random_max_p95_mean_week"] = p
            if not cand["mean_week"] > p:
                cand["fails"].append("G5 random")
            print(f"  candidate {cand['id']}: mean/wk {cand['mean_week']:.5f} vs random-max p95 {p:.5f}", flush=True)
        stage1_ok = bool(cand and not cand["fails"])

        # ---------------- Stage 2: walk-forward of the selection procedure
        folds = []
        for a, bb in FOLDS:
            tr = wk(Wd, "2021-01-01", a)
            te = wk(Wd, a, bb)
            trows = []
            for v in VARIANTS:
                rb, r2, g, _, tv = series[vid(hyp, v)]
                m, m2 = metrics(rb[tr], g[tr]), metrics(r2[tr], g[tr])
                b = metrics(bench[v["L"]][0][tr])
                f = []
                if not ok(m["traded_weeks"], "WF_G1_WEEKS"):
                    f.append("weeks")
                if not ok(m["sharpe"], "WF_SHARPE"):
                    f.append("sharpe")
                if not ok(m2["sharpe"], "WF_SHARPE_2X"):
                    f.append("sharpe_2x")
                f += beats(hyp, m, b, rb[tr], bench[v["L"]][0][tr])
                if not ok(m["maxdd_pct"], "G6_MAXDD"):
                    f.append("maxdd")
                turn = float(tv[tr].mean())
                if not f:
                    trows.append({"id": vid(hyp, v), **v, "sharpe_2x": m2["sharpe"], "turnover": turn})
            pick = select(trows)
            if pick:
                rb = series[pick["id"]][0]
                ret = float(np.prod(1 + rb[te]) - 1)
                bret = float(np.prod(1 + bench[pick["L"]][0][te]) - 1)
            else:
                ret, bret = 0.0, float(np.prod(1 + bench[28][0][te]) - 1)
            folds.append({"test": f"{a}..{bb}", "picked": pick["id"] if pick else None,
                          "train_sharpe_2x": round(pick["sharpe_2x"], 4) if pick else None,
                          "oos_ret_pct": round(ret * 100, 3), "bench_ret_pct": round(bret * 100, 3)})
        oos = float(np.prod([1 + f_["oos_ret_pct"] / 100 for f_ in folds]) - 1) * 100
        boos = float(np.prod([1 + f_["bench_ret_pct"] / 100 for f_ in folds]) - 1) * 100
        pos = sum(1 for f_ in folds if f_["oos_ret_pct"] > 0)
        s2_ok = oos > 0 and ok(pos, "WF_FOLDS_POS") and (hyp == "LS" or oos > boos)
        hres["stage2"] = {"folds": folds, "oos_compounded_pct": round(oos, 3), "bench_compounded_pct": round(boos, 3),
                          "folds_positive": pos, "pass": s2_ok}
        print(f"  walk-forward: OOS {oos:.1f}% (bench {boos:.1f}%), {pos}/8 positive -> {'PASS' if s2_ok else 'FAIL'}",
              flush=True)

        # ---------------- Stage 3
        s3_ok = False
        if stage1_ok and s2_ok:
            v0 = {"L": cand["L"], "K": cand["K"], "filt": cand["filt"]}
            f3, det = [], {}
            for p_, other in (("L", 42 - v0["L"]), ("K", 8 - v0["K"]), ("filt", not v0["filt"])):
                v2 = dict(v0, **{p_: other})
                sh = metrics(series[vid(hyp, v2)][0])["sharpe"]
                det[f"neighbour_{p_}"] = round(sh, 4)
                if not ok(sh, "G8_SHARPE"):
                    f3.append(f"G8 {p_}")
            sh = metrics(S.run("dev", Wd, hyp, v0, exec_="tue")[0])["sharpe"]
            det["tuesday_sharpe"] = round(sh, 4)
            if not ok(sh, "G9_SHARPE"):
                f3.append("G9 late")
            contrib = series[cand["id"]][3]
            best = max(contrib, key=contrib.get)
            sh = metrics(S.run("dev", Wd, hyp, v0, exclude=best)[0])["sharpe"]
            det["without"], det["without_sharpe"] = best, round(sh, 4)
            if not ok(sh, "G10_SHARPE"):
                f3.append("G10 one coin")
            s3_ok = not f3
            hres["stage3"] = {**det, "fails": f3, "pass": s3_ok}
            print(f"  stage 3: {det} -> {f3 or 'PASS'}", flush=True)

        # ---------------- Stage 4
        if s3_ok:
            v0 = {"L": cand["L"], "K": cand["K"], "filt": cand["filt"]}
            print("  stage 4a: opening holdout universe x dev period", flush=True)
            hb1, hb2, hbg, _ = S.run("holdout", Wd, "BENCH", {"L": v0["L"], "K": 0, "filt": False})
            log = {"subs": 0, "delist": []}
            rb, r2, g, _ = S.run("holdout", Wd, hyp, v0, log=log)
            m, m2, b = metrics(rb, g), metrics(r2, g), metrics(hb1)
            f4 = []
            if not ok(m["sharpe"], "G11_SHARPE"):
                f4.append("G11")
            if not ok(m2["sharpe"], "G12_SHARPE_2X"):
                f4.append("G12")
            if hyp == "LO":
                if not (ok(m["sharpe"] - b["sharpe"], "G13_LO_SHARPE_EDGE") and m["maxdd_pct"] <= b["maxdd_pct"]):
                    f4.append("G13")
            else:
                corr = float(np.corrcoef(rb, hb1)[0, 1])
                if not (ok(m["sharpe"], "G13_LS_SHARPE") and ok(m["maxdd_pct"], "G13_LS_MAXDD")
                        and ok(abs(corr), "G13_LS_ABS_CORR")):
                    f4.append("G13")
            hres["stage4a"] = {**rnd(m), "sharpe_2x": round(m2["sharpe"], 4), "benchmark": rnd(b),
                               "delist_events": log["delist"], "substitutions": log["subs"], "fails": f4,
                               "pass": not f4}
            print(f"  stage 4a: {rnd(m)} bench {rnd(b)} -> {f4 or 'PASS'}", flush=True)
            if not f4:
                print("  stage 4b: opening holdout universe x sealed period (once)", flush=True)
                sb1, sb2, _, _ = S.run("holdout", Ws, "BENCH", {"L": v0["L"], "K": 0, "filt": False})
                rb, r2, g, _ = S.run("holdout", Ws, hyp, v0)
                ret2 = float(np.prod(1 + r2) - 1) * 100
                bret2 = float(np.prod(1 + sb2) - 1) * 100
                okb = ok(ret2, "G14_RET_2X") and (hyp == "LS" or ret2 >= bret2)
                hres["stage4b"] = {"weeks": len(Ws), "ret_2x_pct": round(ret2, 3), "bench_ret_2x_pct": round(bret2, 3),
                                   "pass": okb, "note": "validation check only - not evidence of a durable edge"}
                print(f"  stage 4b: {hres['stage4b']}", flush=True)
        hres["validated"] = bool(stage1_ok and s2_ok and s3_ok and hres.get("stage4a", {}).get("pass")
                                 and hres.get("stage4b", {}).get("pass"))
        results["hypotheses"][hyp] = hres

    for L in (14, 28):
        results.setdefault("benchmark_dev", {})[f"L={L}"] = rnd(metrics(bench[L][0]))
    (OUT / "rotation_results.json").write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
    # §13 per-stage files
    for st in ("stage1", "stage2", "stage3", "stage4"):
        keys = ["stage4a", "stage4b"] if st == "stage4" else [st]
        payload = {**meta0, **{h: {k: r.get(k, "not reached") for k in keys + (["candidate"] if st == "stage1" else [])}
                               for h, r in results["hypotheses"].items()}}
        (OUT / f"rotation_{st}.json").write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    print(json.dumps({h: {"candidate": r["candidate"], "stage2": r["stage2"]["pass"],
                          "validated": r["validated"]} for h, r in results["hypotheses"].items()}, indent=1))
    print(f"seconds: {time.time() - t0:.0f}")


if __name__ == "__main__":
    main()
