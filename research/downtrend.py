"""Downtrend specialists. Rules: research/PREREGISTRATION_2026-10-07_downtrend.md (frozen, do not edit).

  .venv\\Scripts\\python.exe research\\downtrend.py fit     # dev coins, entries 2021..2023 -> downtrend/fit.json
  .venv\\Scripts\\python.exe research\\downtrend.py testA   # dev coins, entries 2024-01-01..2026-09-18
  .venv\\Scripts\\python.exe research\\downtrend.py testB   # 280 unseen coins (only rules that passed A)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "downtrend"
FUT = ROOT / "data" / "market" / "dev_1h" / "binance" / "futures"
OOS = ROOT / "data" / "market" / "extra_coins_1h"
sys.path.insert(0, str(HERE))
from regime_switch import market_types  # noqa: E402  (same BTC type definition, unchanged)

FIT = ("2021-01-01", "2024-01-01")
TEST = ("2024-01-01", "2026-09-19")
FIT_HALVES = [("2021-01-01", "2023-01-01"), ("2023-01-01", "2024-01-01")]
TEST_YEARS = [("2024-01-01", "2025-01-01"), ("2025-01-01", "2026-01-01"), ("2026-01-01", "2026-09-19")]
COST = 0.20            # round trip, % of notional (0.10% per side)
STOP_SLIP = 0.05       # extra % on stop fills
EXTRA = 0.20           # 2x costs
MIN_HIST = 60 * 24
SEED, REPS = 20261007, 1000
PAD = 400              # NaN bars between coins in the global arrays (> longest hold 336)

RULES = {   # id: (kind, side, hold_bars, stop_k, params)
    "D0":  ("xs_volume", -1, 24, 2.0, {}),
    "D1a": ("xs_weak", -1, 72, 1.5, {}),
    "D1b": ("xs_weak", -1, 168, 2.0, {}),
    "D2a": ("bounce", -1, 48, 1.5, {"ema": 50}),
    "D2b": ("bounce", -1, 48, 1.5, {"ema": 100}),
    "D3a": ("breakdown", -1, 72, 1.5, {"vol": False}),
    "D3b": ("breakdown", -1, 72, 1.5, {"vol": True}),
    "D4a": ("capitulation", 1, 24, 1.5, {}),
    "D4b": ("capitulation", 1, 48, 1.5, {}),
    "D5a": ("fund_lo", -1, 24, 1.5, {}),
    "D5b": ("fund_lo", -1, 48, 1.5, {}),
    "D6":  ("xs_beta", -1, 336, 2.0, {}),
}


def ts(s):
    return pd.Timestamp(s, tz="UTC")


# ------------------------------------------------------------------ data
def dev_files():
    split = json.loads((ROOT / "data" / "market" / "universe" / "split_140.json").read_text(encoding="utf-8"))
    return [(c, FUT / f"{c}_USDT_USDT-1h-futures.feather", FUT / f"{c}_USDT_USDT-1h-funding_rate.feather")
            for c in split["dev"] + split["holdout"] if (FUT / f"{c}_USDT_USDT-1h-futures.feather").exists()]


def oos_files():
    kept = json.loads((HERE / "pipeline" / "oos_universe.json").read_text(encoding="utf-8"))["kept"]
    return [(s[:-4], OOS / s / "ohlcv_1h.feather", OOS / s / "funding.feather") for s in kept
            if (OOS / s / "ohlcv_1h.feather").exists()]


def ns(s):
    return pd.to_datetime(s, utc=True).astype("datetime64[ns, UTC]")


def load_coin(p, fp) -> pd.DataFrame | None:
    d = pd.read_feather(p)
    d["date"] = ns(d["date"])
    d = d.drop_duplicates("date").set_index("date").sort_index()
    d = d.reindex(pd.date_range(d.index[0], d.index[-1], freq="h"))   # regular grid, gaps NaN
    if len(d) < MIN_HIST + 48:
        return None
    d["fund"] = 0.0
    d["fund_last"] = np.nan
    if fp.exists():
        f = pd.read_feather(fp)
        f["date"] = ns(f["date"])
        f = f.drop_duplicates("date").set_index("date").funding_rate.astype(float)
        f.index = f.index.floor("h")
        f = f[~f.index.duplicated()]
        d.loc[d.index.intersection(f.index), "fund"] = f.reindex(d.index).dropna()
        d["fund_last"] = f.reindex(d.index).ffill()
        d["fund_pct"] = d.fund_last.rolling(90 * 24, min_periods=30 * 24).rank(pct=True)
    else:
        d["fund_pct"] = np.nan
    c = d.close
    d["sigma"] = np.log(c / c.shift(24)).rolling(480, min_periods=240).std()
    d["hist"] = np.arange(len(d))
    d["dv30"] = (c * d.volume).rolling(720, min_periods=360).sum()
    d["vol24"] = d.volume.rolling(24).sum()
    d["vol24_avg30"] = d.vol24.rolling(720, min_periods=360).mean()
    d["ret24"] = c / c.shift(24) - 1
    d["ret168"] = c / c.shift(168) - 1
    d["sma480"] = c.rolling(480).mean()
    d["low480"] = d.low.shift(1).rolling(480).min()
    for n in (50, 100):
        d[f"ema{n}"] = c.ewm(span=n, adjust=False).mean()
    return d


class Universe:
    """All coins concatenated into global arrays (NaN pad between coins) for vectorised trade simulation."""

    def __init__(self, files):
        frames, self.coins = [], []
        for c, p, fp in files:
            try:
                d = load_coin(p, fp)
            except Exception as e:
                print(f"  {c}: load failed {type(e).__name__}")
                continue
            if d is None:
                continue
            d["coin"] = c
            frames.append(d)
            frames.append(pd.DataFrame(index=pd.RangeIndex(PAD)))
            self.coins.append(c)
        g = pd.concat([f.reset_index(names="date") if "close" in f else f for f in frames], ignore_index=True)
        self.g = g
        self.date = g["date"]
        for k in ("open", "high", "low", "close"):
            setattr(self, k, g[k].to_numpy(float))
        self.F = np.nancumsum(g["fund"].fillna(0).to_numpy(float))
        self.ok = g["close"].notna().to_numpy() & g["sigma"].notna().to_numpy() & (g["hist"].fillna(0).to_numpy() >= MIN_HIST)
        print(f"  universe: {len(self.coins)} coins, {len(g)} rows")


def btc_hourly():
    d = pd.read_feather(FUT / "BTC_USDT_USDT-1h-futures.feather")
    d["date"] = ns(d["date"])
    return d.drop_duplicates("date").set_index("date").close.sort_index()


# ------------------------------------------------------------------ signals
def signals(U: Universe, rule: str, types: pd.Series, want: str) -> pd.DataFrame:
    """Entry bars (global index of the entry bar = signal bar + 1) on days of type `want` ('DN' / 'UP')."""
    kind, side, hold, k, prm = RULES[rule]
    g = U.g
    ent = np.arange(len(g)) + 1
    ent_date = U.date.shift(-1)
    day_type = ent_date.dt.floor("D").map(types)
    is_want = day_type.fillna("").str.startswith(want).to_numpy()
    valid = U.ok & is_want & np.r_[U.ok[1:], False]
    if kind == "bounce":
        e = g[f"ema{prm['ema']}"]
        m = (g.close < g.sma480) & (g.high >= e) & (g.close < e) & (g.close < g.open) & (g.close.shift(1) < e.shift(1))
    elif kind == "breakdown":
        m = (g.close < g.low480) & (g.close.shift(1) >= g.low480.shift(1))
        if prm["vol"]:
            m &= g.vol24 >= 2 * g.vol24_avg30
    elif kind == "capitulation":
        m = (g.ret24 <= -2.5 * g.sigma) & (g.vol24 >= 3 * g.vol24_avg30)
        m &= ~m.shift(1, fill_value=False)
    elif kind == "fund_lo":
        m = (g.fund_last < 0) & (g.fund_pct <= 0.05)
        m &= ~m.shift(1, fill_value=False)
    else:
        m = cross_section(U, kind, ent_date, day_type, want)
    idx = np.flatnonzero(m.fillna(False).to_numpy() & valid)
    return pd.DataFrame({"sig": idx, "ent": ent[idx]})


def cross_section(U, kind, ent_date, day_type, want):
    g = U.g
    at00 = (ent_date.dt.hour == 0).to_numpy() & U.ok & np.r_[U.ok[1:], False]
    sub = g.loc[at00, ["coin", "dv30", "ret168", "close"]].copy()
    sub["eday"] = ent_date[at00].dt.floor("D").to_numpy()
    sub["dtype"] = day_type[at00].to_numpy()
    sub = sub[sub.dtype.fillna("").str.startswith(want)]
    pick = pd.Series(False, index=g.index)
    if kind == "xs_volume":
        sel = sub.groupby("eday").dv30.nlargest(20).index.get_level_values(1)
    elif kind == "xs_weak":
        b = btc_hourly()
        b7 = (b / b.shift(168) - 1)
        sig_date = sub.eday - pd.Timedelta(hours=1)
        sub["rel"] = sub.ret168 - sig_date.map(b7).to_numpy()
        sel = sub.dropna(subset=["rel"]).groupby("eday").rel.nsmallest(5).index.get_level_values(1)
    else:  # xs_beta: first DN day after an UP day, top 10 beta (60 daily returns) to BTC
        tdays = day_type.groupby(ent_date.dt.floor("D")).first()
        first = {d for d, t, p in zip(tdays.index, tdays.values, tdays.shift(1).values)
                 if isinstance(t, str) and t.startswith("DN") and isinstance(p, str) and p.startswith("UP")}
        sub = sub[sub.eday.isin(first)]
        b = btc_hourly()
        bd = np.log(b[b.index.hour == 23]).diff()
        betas = []
        start = g.dropna(subset=["coin"]).groupby("coin").apply(lambda s: s.index[0])
        for i, r in sub.iterrows():
            lo = start[r.coin]
            seg = g.loc[max(lo, i - 61 * 24):i]
            seg = seg[pd.to_datetime(seg["date"]).dt.hour == 23]
            cr = np.log(seg.close.astype(float)).diff()
            br = bd.reindex(pd.to_datetime(seg["date"]))
            x = pd.concat([cr.reset_index(drop=True), br.reset_index(drop=True)], axis=1).dropna().tail(60)
            betas.append(np.cov(x.iloc[:, 0], x.iloc[:, 1])[0, 1] / x.iloc[:, 1].var() if len(x) >= 40 else np.nan)
        sub["beta"] = betas
        sel = sub.dropna(subset=["beta"]).groupby("eday").beta.nlargest(10).index.get_level_values(1)
    pick.loc[sel] = True
    return pick


# ------------------------------------------------------------------ simulation
def simulate(U: Universe, ent: np.ndarray, side: int, hold, k: float, sigma_at: np.ndarray) -> pd.DataFrame:
    """Vectorised. hold: int or array of per-trade holds. Returns per-trade P&L in % of notional."""
    n = len(ent)
    if n == 0:
        return pd.DataFrame(columns=["ent", "exit", "pnl", "stopped"])
    H = np.broadcast_to(np.asarray(hold), (n,)).astype(int)
    Hm = int(H.max())
    idx = ent[:, None] + np.arange(Hm)[None, :]
    idx = np.minimum(idx, len(U.close) - 1)
    inside = np.arange(Hm)[None, :] < H[:, None]
    hi, lo, cl = U.high[idx], U.low[idx], U.close[idx]
    e_px = U.open[ent]
    stop = e_px * (1 - side * k * sigma_at)
    hit = (hi >= stop[:, None]) if side < 0 else (lo <= stop[:, None])
    hit &= inside
    nanpath = np.isnan(cl) & inside
    first_hit = np.where(hit.any(1), hit.argmax(1), Hm + 1)
    first_nan = np.where(nanpath.any(1), nanpath.argmax(1), Hm + 1)
    keep = first_nan > np.minimum(first_hit, H - 1)          # data gap before the exit -> drop the trade
    stopped = first_hit < H
    last = np.where(stopped, first_hit, H - 1)
    x_px = np.where(stopped, stop * (1 - side * STOP_SLIP / 100), cl[np.arange(n), last])
    xbar = ent + last
    fund = np.where(stopped, U.F[xbar] - U.F[ent], U.F[np.minimum(xbar + 1, len(U.F) - 1)] - U.F[ent])
    pnl = side * (x_px / e_px - 1) * 100 - COST - side * fund * 100
    out = pd.DataFrame({"ent": ent, "exit": xbar, "pnl": pnl, "stopped": stopped})
    return out[keep & np.isfinite(pnl)]


def no_stack(U, tr: pd.DataFrame) -> pd.DataFrame:
    """One open trade per coin: drop entries while the previous trade on that coin is still open."""
    tr = tr.sort_values("ent")
    keep, last_exit = [], -1
    for e, x in zip(tr.ent.to_numpy(), tr.exit.to_numpy()):
        if e > last_exit:          # global index: coins never overlap (NaN pad), so one cursor works
            keep.append(True)
            last_exit = x
        else:
            keep.append(False)
    return tr[np.array(keep, bool)]


def run_rule(U, rule, types, want, a, b) -> pd.DataFrame:
    kind, side, hold, k, _ = RULES[rule]
    s = signals(U, rule, types, want)
    ent = s.ent.to_numpy()
    d = U.date.iloc[ent]
    m = ((d >= ts(a)) & (d < ts(b))).to_numpy()
    ent, sig = ent[m], s.sig.to_numpy()[m]
    if kind == "xs_beta":
        hold = d_beta_hold(U, ent, types)
    else:
        hold = np.full(len(ent), hold)
    tr = simulate(U, ent, side, hold, k, U.g.sigma.to_numpy(float)[sig])
    tr = no_stack(U, tr)
    tr["date"] = pd.to_datetime(U.date.iloc[tr.ent.to_numpy()].to_numpy(), utc=True)
    tr["day"] = tr["date"].dt.floor("D")
    tr["coin"] = U.g.coin.iloc[tr.ent.to_numpy()].to_numpy()
    tr["dtype"] = tr.day.map(types).to_numpy()
    return tr


def d_beta_hold(U, ent, types):
    """D6: hold until the first UP day (exit at the last bar before it) or 14 days."""
    up_days = sorted(d for d, t in types.items() if isinstance(t, str) and t.startswith("UP"))
    up = pd.DatetimeIndex(up_days)
    out = []
    for e in ent:
        d0 = U.date.iloc[e]
        nxt = up[up > d0]
        bars = int((nxt[0] - d0) / pd.Timedelta(hours=1)) if len(nxt) else 336
        out.append(max(1, min(336, bars)))
    return np.array(out)


# ------------------------------------------------------------------ stats
def pf(p):
    l = -p[p < 0].sum()
    return float(p[p > 0].sum() / l) if l > 0 else None


def day_t(tr):
    x = tr.groupby("day").pnl.mean().to_numpy()
    if len(x) < 3 or x.std(ddof=1) == 0:
        return None
    return float(x.mean() / x.std(ddof=1) * np.sqrt(len(x)))


def stats(tr, periods) -> dict:
    p = tr.pnl.to_numpy()
    out = {"trades": int(len(tr)), "days": int(tr.day.nunique()) if len(tr) else 0,
           "pf": pf(p), "pf_2x": pf(p - EXTRA), "avg": float(p.mean()) if len(p) else None,
           "net": float(p.sum()), "day_t": day_t(tr) if len(tr) else None,
           "win": float((p > 0).mean() * 100) if len(p) else None,
           "stopped_pct": float(tr.stopped.mean() * 100) if len(tr) else None}
    out["periods"] = {}
    for a, b in periods:
        s = tr[(tr.date >= ts(a)) & (tr.date < ts(b))]
        out["periods"][a[:4]] = {"trades": int(len(s)), "net": float(s.pnl.sum())}
    out["by_type"] = {t: {"trades": int((tr.dtype == t).sum()), "net": float(tr[tr.dtype == t].pnl.sum())}
                      for t in ("DN_LOVOL", "DN_HIVOL", "UP_LOVOL", "UP_HIVOL") if (tr.dtype == t).any()}
    return out


def random_pct(U, tr, rule, types, reps=REPS):
    """Same number of trades per entry day, random coins/hours of that day, same side/hold/stop."""
    kind, side, hold, k, _ = RULES[rule]
    rng = np.random.default_rng(SEED)
    okidx = np.flatnonzero(U.ok & np.r_[U.ok[1:], False])
    days = pd.DatetimeIndex(U.date.iloc[okidx].dt.floor("D"))
    by_day = pd.Series(okidx, index=days).groupby(level=0).apply(np.array)
    cnt = tr.groupby("day").size()
    sig = U.g.sigma.to_numpy(float)
    tot = np.zeros(reps)
    for r in range(reps):
        picks = [rng.choice(by_day[d], size=n) for d, n in cnt.items() if d in by_day.index]
        s = np.concatenate(picks) if picks else np.array([], int)
        h = d_beta_hold(U, s + 1, types) if kind == "xs_beta" else hold
        tot[r] = simulate(U, s + 1, side, h, k, sig[s]).pnl.sum()
    return float((tot < tr.pnl.sum()).mean() * 100), float(np.median(tot))


# ------------------------------------------------------------------ stages
def fit():
    OUT.mkdir(exist_ok=True)
    types = market_types()
    U = Universe(dev_files())
    res, surv = {}, []
    for rule in RULES:
        tr = run_rule(U, rule, types, "DN", *FIT)
        s = stats(tr, FIT_HALVES)
        halves = [v["net"] for v in s["periods"].values() if v["trades"] >= 20]
        ok = (s["trades"] >= 100 and (s["pf"] or 0) >= 1.15 and (s["pf_2x"] or 0) >= 1.05
              and (s["day_t"] or 0) >= 2.5 and len(halves) > 0 and all(h > 0 for h in halves))
        s["survives"] = bool(ok)
        if rule != "D6":
            s["same_rule_UP_days"] = stats(run_rule(U, rule, types, "UP", *FIT), FIT_HALVES)
        res[rule] = s
        if ok:
            surv.append(rule)
        print(f"{rule:4} n={s['trades']:6} pf={s['pf'] and round(s['pf'], 3)} pf2x={s['pf_2x'] and round(s['pf_2x'], 3)} "
              f"t={s['day_t'] and round(s['day_t'], 2)} halves={[round(h) for h in halves]} -> {'SURVIVES' if ok else 'out'}",
              flush=True)
    (OUT / "fit.json").write_text(json.dumps({"survivors": surv, "rules": res}, indent=1, default=str), encoding="utf-8")
    print("survivors:", surv or "NONE")


def test(scope: str):
    fitres = json.loads((OUT / "fit.json").read_text(encoding="utf-8"))
    if scope == "B":
        a = json.loads((OUT / "testA.json").read_text(encoding="utf-8"))
        rules = [r for r, v in a["rules"].items() if v["pass"]]
    else:
        rules = fitres["survivors"]
    if not rules:
        print("nothing to test"); return
    types = market_types()
    U = Universe(dev_files() if scope == "A" else oos_files())
    end = TEST[1] if scope == "A" else "2026-09-01"
    years = TEST_YEARS if scope == "A" else TEST_YEARS[:2] + [("2026-01-01", "2026-09-01")]
    out = {}
    for rule in rules:
        tr = run_rule(U, rule, types, "DN", TEST[0], end)
        s = stats(tr, years)
        s["same_rule_UP_days"] = stats(run_rule(U, rule, types, "UP", TEST[0], end), years) if rule != "D6" else None
        chk = {"A1 PF>=1.10 & PF2x>=1.00": (s["pf"] or 0) >= 1.10 and (s["pf_2x"] or 0) >= 1.00,
               "A2 day t>=2": (s["day_t"] or 0) >= 2.0,
               "A3 >=2/3 periods positive": sum(v["net"] > 0 for v in s["periods"].values()) >= 2}
        if rule != "D0":
            s["random_pct"], s["random_median"] = random_pct(U, tr, rule, types)
            chk["A4 random >= p95"] = s["random_pct"] >= 95
        s["checks"], s["pass"] = chk, all(chk.values())
        out[rule] = s
        tr.to_parquet(OUT / f"test{scope}_{rule}.parquet")
        print(json.dumps({rule: s}, indent=1, default=str), flush=True)
    (OUT / f"test{scope}.json").write_text(json.dumps({"rules": out}, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    {"fit": fit, "testA": lambda: test("A"), "testB": lambda: test("B")}[sys.argv[1]]()
