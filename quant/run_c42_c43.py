r"""Batch 7 runner (FAMILIES_C.md "Batch 7", registered 2026-10-18 before this file existed).

    .venv\Scripts\python.exe -m quant.run_c42_c43 dev C42     # generate trades (all periods) + judge DEV only
    .venv\Scripts\python.exe -m quant.run_c42_c43 valid C42   # refused without a recorded DEV pass
    .venv\Scripts\python.exe -m quant.run_c42_c43 wf C42      # refused without a recorded VALID pass

C42 wick catcher: 5m, resting maker limit buys 3 hourly-sigma below the last close (fills only through the limit).
C43 sell the bounce: 4h signal from 1h data, short only, BTC Bear only, rally into the coin's 20-day average rejected.
Universe = the 46 coins of the live bot's whitelist (Michael's fair-test framework, 2026-10-16).
Trades -> runs/c_trades/BATCH7/<tf: 5m | 1h>/<coin>.parquet (+ .twins.npz); results -> runs/ledger_c.jsonl.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import trades as T
from .bars import _fund_into, bars
from .book import replay, metrics
from .eval_c import PERIODS, WALK_FORWARD, ledger, mins
from .paths import DATA, MARKET, ROOT, RUNS

NFI5 = MARKET / "main" / "binance" / "futures"
LIVE_CFG = ROOT / "configs" / "live_coins_2026-10.json"   # the list live in 2026-10 (the C42/C43 runs used the list live at that time)
BATCH = "BATCH7"
REPS = 2000
MAKER = 0.0002
THROUGH = 0.001                      # price must trade 0.1% through a resting limit to count as filled
DEV_END = {"C42": "2025-09-01", "C42M": "2025-09-01", "C43": "2024-07-01"}
TF = {"C42": "5m", "C42M": "1m", "C43": "1h"}


def utc(x) -> pd.Timestamp:
    x = pd.Timestamp(x)
    return x.tz_localize("UTC") if x.tzinfo is None else x.tz_convert("UTC")


def coins() -> list[str]:
    wl = json.loads(LIVE_CFG.read_text(encoding="utf-8"))["pair_whitelist"]
    return sorted(p.split("/")[0] for p in wl)


# ------------------------------------------------------------------ market cells (bullcalm_rule, vectorised)
def btc_daily_cells() -> pd.DataFrame:
    """Per UTC day D: the cell known during day D = computed from the daily candle dated D-1 (closed at D 00:00)."""
    d = pd.read_feather(MARKET / "dev_1h" / "binance" / "futures" / "BTC_USDT_USDT-1d-futures.feather")
    c = d.drop_duplicates("date").sort_values("date").set_index("date")["close"].astype(float)
    ret20 = c / c.shift(20) - 1
    vol20 = c.pct_change().rolling(20).std()
    med = vol20.rolling(365, min_periods=300).median().shift(1)
    out = pd.DataFrame({"bull": ret20 > 0, "calm": vol20 <= med, "ret_ok": ret20.notna(), "vol_ok": med.notna()})
    out.index = out.index + pd.Timedelta(days=1)            # known from the next day on
    return out


def cell_of(ts: pd.Series, cells: pd.DataFrame) -> pd.Series:
    day = pd.to_datetime(ts, utc=True).dt.floor("D")
    x = cells.reindex(day.to_numpy())
    lab = np.where(x["bull"].to_numpy(dtype=bool), "Bull", "Bear").astype(object)
    lab2 = np.where(x["calm"].to_numpy(dtype=bool), "Calm", "Wild").astype(object)
    res = pd.Series([f"{a}-{b}" for a, b in zip(lab, lab2)], index=ts.index)
    res[~x["vol_ok"].fillna(False).to_numpy(dtype=bool)] = "n/a"
    return res


# ------------------------------------------------------------------ C42 wick catcher (5m)
def bars5(coin: str) -> pd.DataFrame:
    h = pd.read_feather(NFI5 / f"{coin}_USDT_USDT-5m-futures.feather")
    h = h.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    h["date"] = h["date"].dt.as_unit("ns")
    df = pd.DataFrame({"date": h["date"], **{k: h[k].astype(float) for k in ("open", "high", "low", "close", "volume")}})
    df["qvol"] = df["close"] * df["volume"]
    fp = NFI5 / f"{coin}_USDT_USDT-1h-funding_rate.feather"
    df["fund"] = 0.0
    if fp.exists():
        f = pd.read_feather(fp)
        if len(f):
            df["fund"] = _fund_into(df["date"], pd.Timedelta(minutes=5), f["date"], f.iloc[:, 1].to_numpy(dtype=float))
    return df


def c42_trades(df: pd.DataFrame, cost_mult: float = 1.0) -> list[dict]:
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    fund, dates, n = df["fund"].to_numpy(), df["date"].to_numpy(), len(df)
    lr = np.log(df["close"]).diff()
    sig_h = (lr.rolling(288).std() * np.sqrt(12)).shift(1).to_numpy()      # known before bar i opens
    prev_c = np.r_[np.nan, c[:-1]]
    lim = prev_c * (1 - 3 * sig_h)
    ok = T.eligible(df, 288)
    cand = np.where(ok & np.isfinite(lim) & (l <= lim * (1 - THROUGH)))[0]
    mk, tk, sx = MAKER * cost_mult, (T.FEE + T.SLIP) * cost_mult, T.STOP_EXTRA * cost_mult
    out, free = [], 0
    for e in cand:
        if e < free:
            continue
        px = min(lim[e], o[e])
        s = sig_h[e]
        stop, tp = px * (1 - 3 * s), px * (1 + 1.5 * s)
        end = min(n - 1, e + 11)                     # 12 bars incl. the entry bar
        if l[e] <= stop:                             # entry bar: stop only (pessimistic), no TP
            x, reason, xp = e, "stop", stop * (1 - sx)
        else:
            x = None
            for j in range(e + 1, end + 1):
                if l[j] <= stop:
                    xp = (o[j] if o[j] < stop else stop) * (1 - sx)
                    x, reason = j, "stop"
                    break
                if h[j] >= tp * (1 + THROUGH):
                    x, reason, xp = j, "tp", tp
                    break
            if x is None:
                x, reason, xp = end, "time", c[end]
        cost = mk + (mk if reason == "tp" else tk + (sx if reason == "stop" else 0.0))
        gross = xp / px - 1
        f = fund[e:x + 1].sum()
        out.append({"side": 1, "entry_i": e, "exit_i": x, "entry_t": dates[e], "exit_t": dates[x],
                    "ret": gross - cost - f, "gross": gross, "funding": f, "cost": cost,
                    "mae": np.nanmin(l[e:x + 1]) / px - 1, "reason": reason, "bars": x - e + 1})
        free = x + 1
    return out


# ------------------------------------------------------------------ C42-1m: identical rule, execution on 1m bars
M1 = DATA / "c42_1m"
M1_URL = "https://data.binance.vision/data/futures/um/monthly/klines/{s}/1m/{s}-1m-{m}.zip"
M1_MONTHS = [str(p) for p in pd.period_range("2024-09", "2025-08", freq="M")]     # DEV only (registered)
MIN5 = np.timedelta64(5, "m")


def c42_levels(df: pd.DataFrame, through: float = THROUGH) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(sig_h, lim, candidate 5m indices) exactly as c42_trades computes them."""
    c, l = df["close"].to_numpy(), df["low"].to_numpy()
    lr = np.log(df["close"]).diff()
    sig_h = (lr.rolling(288).std() * np.sqrt(12)).shift(1).to_numpy()
    lim = np.r_[np.nan, c[:-1]] * (1 - 3 * sig_h)
    cand = np.where(T.eligible(df, 288) & np.isfinite(lim) & (l <= lim * (1 - through)))[0]
    return sig_h, lim, cand


def fetch_1m(coin: str, df: pd.DataFrame, f_out=None, through: float = THROUGH, months=None,
             lo=np.datetime64("2024-09-01"), hi=np.datetime64("2025-09-01")) -> pd.DataFrame:
    """1m klines for the 60 minutes after every candidate 5m bar (C42-1m default: DEV, data/c42_1m/<coin>.parquet).
    C44 passes its own cache file, through=0 (sell-stop triggers on a touch) and its months / period."""
    import io
    import urllib.error
    import urllib.request
    import zipfile
    f_out = f_out or M1 / f"{coin}.parquet"
    if f_out.exists():
        return pd.read_parquet(f_out)
    f_out.parent.mkdir(parents=True, exist_ok=True)
    _, _, cand = c42_levels(df, through)
    starts = df["date"].to_numpy()[cand].astype("datetime64[m]")
    starts = starts[(starts >= lo) & (starts < hi)]
    want = np.unique((starts[:, None] + np.arange(60).astype("timedelta64[m]")).ravel())
    parts = []
    for m in months or M1_MONTHS:
        url = M1_URL.format(s=f"{coin}USDT", m=m)
        try:
            raw = urllib.request.urlopen(url, timeout=120).read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            k = pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=range(6))
        k = k[pd.to_numeric(k[0], errors="coerce").notna()].astype(float)        # drop a header row if present
        k.columns = ["t", "open", "high", "low", "close", "volume"]
        k["date"] = pd.to_datetime(k["t"].astype("int64"), unit="ms").astype("datetime64[ns]")
        k = k[np.isin(k["date"].to_numpy().astype("datetime64[m]"), want)]
        parts.append(k[["date", "open", "high", "low", "close"]])
    m1 = pd.concat(parts, ignore_index=True).drop_duplicates("date").sort_values("date") if parts else \
        pd.DataFrame(columns=["date", "open", "high", "low", "close"])
    m1.to_parquet(f_out)
    return m1


def c42m_trades(df: pd.DataFrame, m1: pd.DataFrame, cost_mult: float = 1.0, stats: dict | None = None) -> list[dict]:
    o5, l5, h5 = (df[k].to_numpy() for k in ("open", "low", "high"))
    fund = df["fund"].to_numpy()
    d5 = df["date"].to_numpy().astype("datetime64[m]") if df["date"].dt.tz is None else \
        df["date"].dt.tz_localize(None).to_numpy().astype("datetime64[m]")
    sig_h, lim, cand = c42_levels(df)
    lo, hi = np.datetime64("2024-09-01"), np.datetime64("2025-09-01")
    cand = cand[(d5[cand] >= lo) & (d5[cand] < hi)]
    mt = m1["date"].to_numpy().astype("datetime64[m]")
    mo, mh, ml, mc = (m1[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    mk, tk, sx = MAKER * cost_mult, (T.FEE + T.SLIP) * cost_mult, T.STOP_EXTRA * cost_mult
    st = stats if stats is not None else {}
    out, free, n = [], 0, len(df)
    for e in cand:
        if e < free:
            continue
        if e + 11 >= n:
            continue
        a = np.searchsorted(mt, d5[e])
        b = np.searchsorted(mt, d5[e] + np.timedelta64(60, "m"))
        if b - a != 60 or mt[a] != d5[e]:                                  # 1m data incomplete -> skip, never guess
            st["skipped_missing"] = st.get("skipped_missing", 0) + 1
            continue
        w_o, w_h, w_l, w_c = mo[a:b], mh[a:b], ml[a:b], mc[a:b]
        bar5 = np.arange(60) // 5
        mism = any(abs(w_l[bar5 == j].min() - l5[e + j]) > 1e-9 * l5[e + j] or
                   abs(w_h[bar5 == j].max() - h5[e + j]) > 1e-9 * h5[e + j] for j in range(12))
        if mism:                                                          # 1m does not reproduce 5m -> skip
            st["skipped_mismatch"] = st.get("skipped_mismatch", 0) + 1
            continue
        L, s = lim[e], sig_h[e]
        hit = np.where(w_l[:5] <= L * (1 - THROUGH))[0]
        k = int(hit[0])
        px = min(L, w_o[k])
        stop, tp = px * (1 - 3 * s), px * (1 + 1.5 * s)
        if w_l[k] <= stop:                                                # fill minute: stop only (pessimistic)
            x, reason, xp = k, "stop", stop * (1 - sx)
        else:
            x = None
            for j in range(k + 1, 60):
                if w_l[j] <= stop:
                    xp = (w_o[j] if w_o[j] < stop else stop) * (1 - sx)
                    x, reason = j, "stop"
                    break
                if w_h[j] >= tp * (1 + THROUGH):
                    x, reason, xp = j, "tp", tp
                    break
            if x is None:
                x, reason, xp = 59, "time", w_c[59]
        x5 = e + x // 5
        cost = mk + (mk if reason == "tp" else tk + (sx if reason == "stop" else 0.0))
        gross = xp / px - 1
        f = fund[e:x5 + 1].sum()
        st["used"] = st.get("used", 0) + 1
        out.append({"side": 1, "entry_i": e, "exit_i": x5, "entry_t": mt[a + k], "exit_t": mt[a + x],
                    "ret": gross - cost - f, "gross": gross, "funding": f, "cost": cost,
                    "mae": np.nanmin(w_l[k:x + 1]) / px - 1, "reason": reason, "bars": x5 - e + 1,
                    "fill_min": k, "exit_min": x})
        free = x5 + 1
    return out


# ------------------------------------------------------------------ C43 sell the bounce (4h signal on 1h bars)
def c43_signal(df: pd.DataFrame, bear_day: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """Returns (short_sig, atr4) on the 1h index; signal on the 1h bar whose close = the 4h close."""
    d = df.set_index("date")
    f = d.resample("4h", origin="epoch", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "count"})
    f = f[f["volume"] == 4].rename(columns={"volume": "n"})            # complete 4h bars only
    f = f.reset_index()
    sma = f["close"].rolling(120).mean()
    below6 = (f["close"] < sma).astype(float).shift(1).rolling(6).sum() == 6
    ret20 = f["close"] / f["close"].shift(120) - 1
    close_t = f["date"] + pd.Timedelta(hours=4)
    bear = bear_day.reindex(close_t.dt.floor("D").to_numpy()).to_numpy()
    bear = np.nan_to_num(bear.astype(float), nan=0).astype(bool)
    sig4 = below6 & (ret20 < 0) & (f["high"] >= sma) & (f["close"] < sma) & bear
    atr4 = T.atr(f.rename(columns={}))
    last_h = f["date"] + pd.Timedelta(hours=3)                           # open of the 4th 1h bar
    pos = pd.Index(df["date"]).get_indexer(last_h)
    sig = np.zeros(len(df), bool)
    a = np.full(len(df), np.nan)
    m = (pos >= 0) & sig4.to_numpy()
    sig[pos[m]] = True
    a[pos[pos >= 0]] = atr4[pos >= 0]
    return sig, a


def bear_days(cells: pd.DataFrame) -> pd.Series:
    return (~cells["bull"]) & cells["ret_ok"]


# ------------------------------------------------------------------ twins
def twins_c42(df: pd.DataFrame, tr: list[dict], rng) -> np.ndarray:
    if not tr:
        return np.zeros(REPS)
    o, c = df["open"].to_numpy(), df["close"].to_numpy()
    b = np.array([t["bars"] for t in tr])
    cost = np.array([t["cost"] for t in tr])
    lo, hi = tr[0]["entry_i"], tr[-1]["exit_i"]
    span = np.maximum(hi - b + 1 - lo, 1)
    out = np.zeros(REPS)
    for r in range(REPS):
        e = lo + (rng.random(len(b)) * span).astype(int)
        x = np.minimum(e + b - 1, len(c) - 1)
        out[r] = np.nansum(c[x] / o[e] - 1 - cost)
    return out


def twins_c43(df: pd.DataFrame, tr: list[dict], bear_mask: np.ndarray, rng) -> np.ndarray:
    if not tr:
        return np.zeros(REPS)
    o, c = df["open"].to_numpy(), df["close"].to_numpy()
    b = np.array([t["bars"] for t in tr])
    lo, hi = tr[0]["entry_i"], tr[-1]["exit_i"]
    pool = np.where(bear_mask[lo:hi + 1])[0] + lo
    if not len(pool):
        return np.zeros(REPS)
    cost = 2 * (T.FEE + T.SLIP)
    out = np.zeros(REPS)
    for r in range(REPS):
        e = pool[(rng.random(len(b)) * len(pool)).astype(int)]
        x = np.minimum(e + b - 1, len(c) - 1)
        out[r] = np.nansum(-(c[x] / o[e] - 1) - cost)
    return out


# ------------------------------------------------------------------ generation
def generate(fam: str) -> None:
    out_dir = RUNS / "c_trades" / BATCH / TF[fam]
    out_dir.mkdir(parents=True, exist_ok=True)
    dev_end = pd.Timestamp(DEV_END[fam], tz="UTC")
    cells = btc_daily_cells()
    bd = bear_days(cells)
    for coin in coins():
        f_out = out_dir / f"{coin}.parquet"
        if f_out.exists():
            continue
        rng = np.random.default_rng(abs(hash((coin, fam))) % 2**32)
        if fam == "C42M":
            df = bars5(coin)
            m1 = fetch_1m(coin, df)
            st = {}
            tr = c42m_trades(df, m1, stats=st)
            tw = twins_c42(df, tr, rng)
            tr2 = {t["entry_i"]: t for t in c42m_trades(df, m1, 2.0)}
            for t in tr:
                t2 = tr2.get(t["entry_i"])
                t["ret_x2"] = t2["ret"] if t2 is not None and t2["exit_min"] == t["exit_min"] else t["ret"] - t["cost"]
            (out_dir / f"{coin}.parity.json").write_text(json.dumps(st), encoding="utf-8")
        elif fam == "C42":
            df = bars5(coin)
            tr = c42_trades(df)
            dev = [t for t in tr if utc(t["entry_t"]) < dev_end
                   and utc(t["entry_t"]) >= pd.Timestamp(PERIODS["intra"]["dev"][0][1], tz="UTC")]
            tw = twins_c42(df, dev, rng)
            # 2x-cost twin of each trade: same path, every cost doubled (stored for the 2x gate)
            tr2 = {t["entry_i"]: t for t in c42_trades(df, 2.0)}
            for t in tr:
                t2 = tr2.get(t["entry_i"])
                t["ret_x2"] = t2["ret"] if t2 is not None and t2["exit_i"] == t["exit_i"] else t["ret"] - t["cost"]
        else:
            df = bars(coin, "1h")
            sig, a = c43_signal(df, bd)
            tr = T.simulate(df, np.zeros(len(df), bool), sig, T.Exit(2.0, 3.0, 72), a, 24)
            bear_mask = np.nan_to_num(bd.reindex(df["date"].dt.tz_localize("UTC").dt.floor("D").to_numpy()
                                                 if df["date"].dt.tz is None else df["date"].dt.floor("D").to_numpy())
                                      .to_numpy(dtype=float), nan=0).astype(bool)
            dev = [t for t in tr if utc(t["entry_t"]) < dev_end]
            tw = twins_c43(df, dev, bear_mask, rng)
            for t in tr:
                t["cost"] = 2 * (T.FEE + T.SLIP) + (T.STOP_EXTRA if t["reason"] == "stop" else 0.0)
                t["ret_x2"] = t["ret"] - t["cost"]
        for t in tr:
            t["family"], t["coin"] = fam, coin
        res = pd.DataFrame(tr)
        if len(res):
            res = res.drop(columns=["entry_i", "exit_i"])
        res.to_parquet(f_out)
        np.savez(out_dir / f"{coin}.twins.npz", **{fam: tw})
        print(f"  {fam} {coin}: {len(tr)} trades", flush=True)


def load(fam: str, a: str, b: str) -> tuple[pd.DataFrame, np.ndarray]:
    d = RUNS / "c_trades" / BATCH / TF[fam]
    parts, tw = [], np.zeros(REPS)
    lo, hi = pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC")
    for f in sorted(d.glob("*.parquet")):
        x = pd.read_parquet(f)
        if len(x):
            for c in ("entry_t", "exit_t"):
                x[c] = pd.to_datetime(x[c], utc=True)
            parts.append(x[(x["entry_t"] >= lo) & (x["entry_t"] < hi)])
        z = d / f"{f.stem}.twins.npz"
        if z.exists():
            tw = tw + np.load(z)[fam]
    return pd.concat(parts, ignore_index=True), tw


# ------------------------------------------------------------------ evaluation
def counted_periods(bt: pd.DataFrame, periods) -> dict:
    tk = bt[bt["taken"]]
    out = {}
    for name, a, b in periods:
        w = tk[(tk["exit_t"] >= pd.Timestamp(a, tz="UTC")) & (tk["exit_t"] < pd.Timestamp(b, tz="UTC"))]
        out[name] = {"trades": int(len(w)), "pnl": round(float(w["pnl"].sum()), 2)}
    return out


def by_cell(bt: pd.DataFrame, cells: pd.DataFrame) -> dict:
    tk = bt[bt["taken"]].copy()
    if not len(tk):
        return {}
    tk["cell"] = cell_of(tk["entry_t"], cells)
    out = {}
    for k, g in tk.groupby("cell"):
        w, lo = g.loc[g["pnl"] > 0, "pnl"].sum(), -g.loc[g["pnl"] < 0, "pnl"].sum()
        out[k] = {"trades": int(len(g)), "pnl": round(float(g["pnl"].sum()), 2), "pf": round(float(w / max(lo, 1e-9)), 3),
                  "avg_pct": round(float(g["ret"].mean() * 100), 3)}
    return out


def evaluate(fam: str, t: pd.DataFrame, periods, mn: dict, twin: np.ndarray | None) -> dict:
    out = {}
    bt, curve = replay(t, mn)
    out["book"] = metrics(bt, curve, periods)
    out["periods_detail"] = counted_periods(bt, periods)
    out["by_cell"] = by_cell(bt, btc_daily_cells())
    t2 = t.copy()
    t2["ret"] = t2["ret_x2"]
    b2, c2 = replay(t2, mn)
    out["book_x2"] = {k: v for k, v in metrics(b2, c2, periods).items() if k in ("final", "pf", "max_dd_pct", "sharpe")}
    for lev in (2, 3):
        bl, cl = replay(t, mn, lev=lev)
        m = {k: v for k, v in metrics(bl, cl, periods).items() if k in ("final", "pf", "max_dd_pct", "sharpe")}
        m["liquidations"] = int((bl["taken"] & bl["liquidated"]).sum()) if len(bl) else 0
        out[f"book_lev{lev}"] = m
    g = t["gross"]
    out["all_signals"] = {"trades": int(len(t)),
                          "pf_per_trade": round(float(t.loc[t.ret > 0, "ret"].sum() / max(1e-9, -t.loc[t.ret < 0, "ret"].sum())), 3),
                          "gross_pf": round(float(g[g > 0].sum() / max(1e-9, -g[g < 0].sum())), 3),
                          "mean_ret_pct": round(float(t["ret"].mean() * 100), 3),
                          "mean_gross_pct": round(float(g.mean() * 100), 3),
                          "exits": t["reason"].value_counts().to_dict()}
    if twin is not None:
        out["twin_pct"] = round(float((twin < t["ret"].sum()).mean() * 100), 1)
    return out


def period_gate(fam: str, r: dict, need_share: float, min_counted: int, plain_need: int) -> tuple[bool, str]:
    det = r["periods_detail"]
    if fam != "C43":
        pos = sum(v["pnl"] > 0 for v in det.values())
        return pos >= plain_need, f"≥{plain_need} of {len(det)} periods positive"
    cnt = {k: v for k, v in det.items() if v["trades"] >= 10}
    pos = sum(v["pnl"] > 0 for v in cnt.values())
    ok = len(cnt) >= min_counted and pos >= need_share * len(cnt)
    return ok, f"positive in ≥{need_share:.1%} of counted periods (≥10 trades), ≥{min_counted} counted"


# ------------------------------------------------------------------ C44 wick follow (short), judged on VALID only
C44_DIR = DATA / "c44_1m"
C44_SPLIT = {"dev": ("2024-09-01", "2025-09-01", [str(p) for p in pd.period_range("2024-09", "2025-08", freq="M")]),
             "valid": ("2025-09-01", "2026-03-26", [str(p) for p in pd.period_range("2025-09", "2026-03", freq="M")])}


def c44_trades(df: pd.DataFrame, m1: pd.DataFrame, lo: str, hi: str, cost_mult: float = 1.0,
               stats: dict | None = None) -> list[dict]:
    h5, l5 = df["high"].to_numpy(), df["low"].to_numpy()
    fund = df["fund"].to_numpy()
    d5 = df["date"].dt.tz_localize(None).to_numpy().astype("datetime64[m]")
    sig_h, lim, cand = c42_levels(df, 0.0)
    cand = cand[(d5[cand] >= np.datetime64(lo)) & (d5[cand] < np.datetime64(hi))]
    mt = m1["date"].to_numpy().astype("datetime64[m]")
    mo, mh, ml, mc = (m1[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    tk, sx, mk = (T.FEE + T.SLIP) * cost_mult, T.STOP_EXTRA * cost_mult, MAKER * cost_mult
    st = stats if stats is not None else {}
    out, free, n = [], 0, len(df)
    for e in cand:
        if e < free or e + 11 >= n:
            continue
        a = np.searchsorted(mt, d5[e])
        b = np.searchsorted(mt, d5[e] + np.timedelta64(60, "m"))
        if b - a != 60 or mt[a] != d5[e]:                       # 1m data incomplete -> skip, never guess
            st["skipped_missing"] = st.get("skipped_missing", 0) + 1
            continue
        w_o, w_h, w_l, w_c = mo[a:b], mh[a:b], ml[a:b], mc[a:b]
        bar5 = np.arange(60) // 5
        if any(abs(w_l[bar5 == j].min() - l5[e + j]) > 1e-9 * l5[e + j] or
               abs(w_h[bar5 == j].max() - h5[e + j]) > 1e-9 * h5[e + j] for j in range(12)):
            st["skipped_mismatch"] = st.get("skipped_mismatch", 0) + 1
            continue
        L, s = lim[e], sig_h[e]
        k = int(np.where(w_l[:5] <= L)[0][0])
        px = min(L, w_o[k])                                     # trigger level, or the open if it gapped below
        stop, tp = px * (1 + 1.5 * s), px * (1 - 3 * s)
        if w_c[k] >= stop:                                      # fill minute closes above the stop -> surely stopped
            x, reason, xp = k, "stop", stop
        else:
            x = None
            for j in range(k + 1, 60):
                if w_h[j] >= stop:
                    xp, x, reason = (w_o[j] if w_o[j] > stop else stop), j, "stop"
                    break
                if w_l[j] <= tp * (1 - THROUGH):
                    x, reason, xp = j, "tp", tp
                    break
            if x is None:
                x, reason, xp = 59, "time", w_c[59]
        x5 = e + x // 5
        # entry is a taker sell-stop (fee + slippage); TP maker; stop / time taker (+ stop extra)
        cost = tk + (mk if reason == "tp" else tk + (sx if reason == "stop" else 0.0))
        gross = -(xp / px - 1)
        f = fund[e:x5 + 1].sum()                                # shorts receive positive funding
        st["used"] = st.get("used", 0) + 1
        out.append({"side": -1, "entry_i": e, "exit_i": x5, "entry_t": mt[a + k], "exit_t": mt[a + x],
                    "ret": gross - cost + f, "gross": gross, "funding": -f, "cost": cost,
                    "mae": -(np.nanmax(w_h[k:x + 1]) / px - 1), "reason": reason, "bars": x5 - e + 1,
                    "fill_min": k, "exit_min": x})
        free = x5 + 1
    return out


def twins_c44(df: pd.DataFrame, tr: list[dict], lo: str, hi: str, rng) -> np.ndarray:
    """Random twins: same coin, short, same holding (5m bars) and cost, entry at a random 5m open in the period."""
    if not tr:
        return np.zeros(REPS)
    o, c = df["open"].to_numpy(), df["close"].to_numpy()
    d5 = df["date"].dt.tz_localize(None).to_numpy()
    b = np.array([t["bars"] for t in tr])
    cost = np.array([t["cost"] for t in tr])
    pool = np.where((d5 >= np.datetime64(lo)) & (d5 < np.datetime64(hi)))[0]
    pool = pool[pool + b.max() < len(c)]
    out = np.zeros(REPS)
    for r in range(REPS):
        e = pool[(rng.random(len(b)) * len(pool)).astype(int)]
        out[r] = np.nansum(-(c[e + b - 1] / o[e] - 1) - cost)
    return out


def run_c44() -> int:
    mn = mins()
    res = {}
    for split in ("dev", "valid"):
        lo, hi, months = C44_SPLIT[split]
        rows, tw, par = [], np.zeros(REPS), {}
        for i, coin in enumerate(coins()):
            df = bars5(coin)
            m1 = fetch_1m(coin, df, C44_DIR / f"{coin}_{split}.parquet", 0.0, months, np.datetime64(lo), np.datetime64(hi))
            st = {}
            tr = c44_trades(df, m1, lo, hi, stats=st)
            x2 = {t["entry_i"]: t for t in c44_trades(df, m1, lo, hi, 2.0)}
            for t in tr:
                t2 = x2.get(t["entry_i"])
                t["ret_x2"] = t2["ret"] if t2 is not None and t2["exit_min"] == t["exit_min"] else t["ret"] - t["cost"]
                t["family"], t["coin"] = "C44", coin
            rng = np.random.default_rng([i, 44, 0 if split == "dev" else 1])
            tw = tw + twins_c44(df, tr, lo, hi, rng)
            for k, v in st.items():
                par[k] = par.get(k, 0) + v
            rows += tr
            print(f"  C44 {split} {coin}: {len(tr)} trades", flush=True)
        t = pd.DataFrame(rows).drop(columns=["entry_i", "exit_i"])
        for c in ("entry_t", "exit_t"):
            t[c] = pd.to_datetime(t[c], utc=True)
        out_dir = RUNS / "c_trades" / "C44" / ("dev_in_sample" if split == "dev" else "1m")
        out_dir.mkdir(parents=True, exist_ok=True)
        for coin, g in t.groupby("coin"):
            g.to_parquet(out_dir / f"{coin}.parquet")
        r = evaluate("C44", t, PERIODS["intra"][split], mn, tw)
        r["parity"], r["fill_minute"] = par, t["fill_min"].value_counts().sort_index().to_dict()
        res[split] = r
    v, m = res["valid"], res["valid"]["book"]
    g = {"≥100 trades": m.get("trades", 0) >= 100, "PF ≥ 1.10": m.get("pf", 0) >= 1.10, "profit": m.get("final", 0) > 300,
         "profit at 2x costs": v["book_x2"].get("final", 0) > 300, "DD ≤ 40%": m.get("max_dd_pct", 100) <= 40,
         "beats 95% of random twins": v.get("twin_pct", 0) >= 95,
         "Q5 and Q6 positive": all(x["pnl"] > 0 for x in v["periods_detail"].values())}
    verdict = "PASS VALID" if all(g.values()) else "FAIL VALID"
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ledger({"at": stamp, "batch": BATCH, "family": "C44", "tf": "1m", "stage": "valid", "result": v, "gates": g,
            "verdict": verdict, "dev_in_sample": res["dev"]})
    keys = ("book", "book_x2", "periods_detail", "by_cell", "all_signals", "parity", "fill_minute", "twin_pct")
    print(json.dumps({"DEV (in-sample, report only)": {k: res["dev"].get(k) for k in keys},
                      "VALID (judge)": {k: v.get(k) for k in keys}, "gates": g}, indent=1, default=str))
    print("VERDICT: C44", verdict)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["dev", "valid", "wf", "c44"])
    ap.add_argument("family", nargs="?", choices=["C42", "C42M", "C43"])
    a = ap.parse_args()
    if a.stage == "c44":
        return run_c44()
    fam, tf = a.family, TF[a.family]
    key = "1h" if fam == "C43" else "intra"
    mn = mins()
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = [json.loads(l) for l in open(RUNS / "ledger_c.jsonl", encoding="utf-8")]
    mine = lambda stage, verdict: any(r["family"] == fam and r.get("batch") == BATCH and r["stage"] == stage
                                      and r["verdict"] == verdict for r in rows)
    if a.stage == "dev":
        generate(fam)
        per = PERIODS[key]["dev"]
        t, tw = load(fam, per[0][1], per[-1][2])
        r = evaluate(fam, t, per, mn, tw)
        if fam == "C42M":
            par = [json.loads(f.read_text(encoding="utf-8")) for f in (RUNS / "c_trades" / BATCH / tf).glob("*.parity.json")]
            r["parity"] = {k: sum(x.get(k, 0) for x in par) for k in ("used", "skipped_missing", "skipped_mismatch")}
            r["fill_minute"] = t["fill_min"].value_counts().sort_index().to_dict()
        m = r["book"]
        pg, pg_name = period_gate(fam, r, 0.75, 2, 3)
        g = {"≥200 trades": m.get("trades", 0) >= 200, "PF ≥ 1.15": m.get("pf", 0) >= 1.15,
             "PF ≥ 1.0 at 2x costs": r["book_x2"].get("pf", 0) >= 1.0, "DD ≤ 35%": m.get("max_dd_pct", 100) <= 35,
             pg_name: pg, "beats 95% of random twins": r.get("twin_pct", 0) >= 95,
             "top coin ≤ 20% of profit": (m.get("top_coin_share") or 1) <= 0.20}
        verdict = "PASS DEV" if all(g.values()) else "FAIL DEV"
    elif fam == "C42M":
        raise SystemExit("C42M: 1m data exists for DEV only (registered); VALID/WF data is fetched only after a DEV pass")
    elif a.stage == "valid":
        if not mine("dev", "PASS DEV"):
            raise SystemExit("no DEV pass recorded - VALID refused")
        per = PERIODS[key]["valid"]
        t, _ = load(fam, per[0][1], per[-1][2])
        r = evaluate(fam, t, per, mn, None)
        m = r["book"]
        g = {"PF ≥ 1.10": m["pf"] >= 1.10, "profit": m["final"] > 300, "profit at 2x costs": r["book_x2"]["final"] > 300,
             "DD ≤ 40%": m["max_dd_pct"] <= 40}
        verdict = "PASS VALID" if all(g.values()) else "FAIL VALID"
    else:
        if not mine("valid", "PASS VALID"):
            raise SystemExit("no VALID pass recorded - WALK-FORWARD refused")
        periods, need = WALK_FORWARD[key]
        t, _ = load(fam, periods[0][1], periods[-1][2])
        r = evaluate(fam, t, periods, mn, None)
        pg, pg_name = period_gate(fam, r, 5 / 8, 3, need)
        g = {pg_name: pg}
        verdict = "PASS WALK-FORWARD" if pg else "FAIL WALK-FORWARD"
    ledger({"at": stamp, "batch": BATCH, "family": fam, "tf": tf, "stage": a.stage, "result": r, "gates": g,
            "verdict": verdict})
    print(json.dumps({k: r[k] for k in ("book", "book_x2", "periods_detail", "by_cell", "all_signals", "book_lev2", "parity", "fill_minute")
                      if k in r} | {"twin_pct": r.get("twin_pct"), "gates": g}, indent=1, default=str))
    print("VERDICT:", fam, verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
