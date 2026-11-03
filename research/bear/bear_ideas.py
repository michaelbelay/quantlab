"""Bear ideas batch 1 (B1-B6), step 1 signal test. Rules: RULES_BEAR.md, REGISTER_BEAR_IDEAS_2026-11-01.md.

    .venv\\Scripts\\python.exe research\\bear\\bear_ideas.py

Output: research/bear/batch1/trades_<idea>.csv, report.json, REPORT.md. Nothing here is tuned after the run.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / "batch1"
DATA = ROOT / "data" / "market" / "main" / "binance" / "futures"
START, MID, END = pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2024-05-01", tz="UTC"), pd.Timestamp("2026-10-01", tz="UTC")
COST = 0.002
MEMES = {"1000PEPE", "FARTCOIN", "PENGU", "TRUMP", "WIF"}
H = pd.date_range(START, END - pd.Timedelta(hours=1), freq="h")      # bar open times


def coins() -> list[str]:
    s = set()
    for f in ("universe_coins.json", "live_coins_2026-10.json"):
        s |= {p.split("/")[0] for p in json.loads((ROOT / "configs" / f).read_text(encoding="utf-8"))["pair_whitelist"]}
    return sorted(s - MEMES)


def load(c: str):
    f = DATA / f"{c}_USDT_USDT-1h-futures.feather"
    if not f.exists():
        return None
    d = pd.read_feather(f).drop_duplicates("date").set_index("date").sort_index().reindex(H)
    fr = DATA / f"{c}_USDT_USDT-1h-funding_rate.feather"
    fund = pd.read_feather(fr).drop_duplicates("date").set_index("date").funding_rate if fr.exists() else pd.Series(dtype=float)
    return d, fund


# ------------------------------------------------------------------ panels
NAMES = coins()
RAW = {c: x for c in NAMES if (x := load(c)) is not None}
NO_DATA = [c for c in NAMES if c not in RAW]
COLS = list(RAW)
O, Hi, Lo, C, V = (pd.DataFrame({c: RAW[c][0][k] for c in COLS}) for k in ("open", "high", "low", "close", "volume"))
FUND = {c: RAW[c][1] for c in COLS}
SMA = C.rolling(480, min_periods=480).mean()
QV24 = (C * V).rolling(24, min_periods=24).sum()
ELIG = (QV24 >= 1e7) & C.notna()
AGE = C.notna().cumsum()                                              # hours of history

# bear day: BTC 20-day return <= 0 at the last completed UTC daily close (close of the 23:00 bar of the day before)
btc = C["BTC"]
dclose = btc[btc.index.hour == 23]
dclose.index = dclose.index.normalize() + pd.Timedelta(days=1)       # known from the start of the next day
bear_day = (dclose / dclose.shift(20) - 1 <= 0)
BEAR = pd.Series(H.normalize().map(bear_day).fillna(False).astype(bool).to_numpy(), index=H)
# an entry at the close of bar t happens at t+1h: use the bear flag of that moment
BEAR_AT_CLOSE = pd.Series(BEAR.shift(-1, fill_value=False).to_numpy(), index=H)

T = H + pd.Timedelta(hours=1)                                          # close times


def funding_sum(c: str, t0: pd.Timestamp, t1: pd.Timestamp) -> float:
    f = FUND[c]
    if f.empty:
        return 0.0
    return float(f[(f.index > t0) & (f.index <= t1)].sum())


def trade(c: str, i: int, side: int, stop: float, target: float | None, hold: int) -> dict | None:
    """Enter at close of bar i; stop checked before target in every later bar; else exit at close of bar i+hold."""
    n = len(H)
    if i + 1 >= n:
        return None
    e = C[c].iat[i]
    hi, lo, cl = Hi[c].to_numpy(), Lo[c].to_numpy(), C[c].to_numpy()
    j_end = min(i + hold, n - 1)
    px, why, j = cl[j_end], "time", j_end
    for j in range(i + 1, j_end + 1):
        if np.isnan(cl[j]):
            px, why = cl[j - 1], "data end"
            j -= 1
            break
        if side < 0 and hi[j] >= stop or side > 0 and lo[j] <= stop:
            px, why = stop, "stop"
            break
        if target is not None and (side < 0 and lo[j] <= target or side > 0 and hi[j] >= target):
            px, why = target, "target"
            break
    else:
        j = j_end
    gross = side * (px / e - 1)
    fund = -side * funding_sum(c, T[i], T[j])
    return {"coin": c, "entry": T[i], "exit": T[j], "side": "short" if side < 0 else "long", "entry_px": e, "exit_px": px,
            "why": why, "gross": gross, "funding": fund, "net": gross + fund - COST, "net2x": gross + fund - 2 * COST, "_j": j}


def run_rule(sig: pd.DataFrame, make, gap: int = 0) -> list[dict]:
    out = []
    for c in COLS:
        idx = np.flatnonzero(sig[c].to_numpy())
        busy, last = -1, -10 ** 9
        for i in idx:
            if i <= busy or i - last < gap:
                continue
            t = make(c, i)
            if t:
                out.append(t)
                busy, last = t.pop("_j"), i
    return out


def base_mask() -> pd.DataFrame:
    return ELIG & pd.DataFrame(np.repeat(BEAR_AT_CLOSE.to_numpy()[:, None], len(COLS), 1), index=H, columns=COLS)


# ------------------------------------------------------------------ ideas
def b1():
    h24 = Hi.rolling(24).max()
    l72 = Lo.rolling(72).min()
    prior_hi = Hi.shift(24).rolling(168).max()
    sig = base_mask() & (C < SMA) & (h24 >= l72 * 1.08) & (h24 < prior_hi) & (C < Lo.shift(1).rolling(6).min()) & (C <= h24 * 0.97)

    def make(c, i):
        e, st = C[c].iat[i], h24[c].iat[i] * 1.01
        return trade(c, i, -1, st, e - 2 * (st - e), 72)
    return run_rule(sig, make, gap=24)


def b2():
    sett = pd.Series(np.isin(T.hour, (0, 8, 16)), index=H)
    fl = pd.DataFrame({c: FUND[c].reindex(T).to_numpy() if not FUND[c].empty else np.nan for c in COLS}, index=H)
    sig = base_mask() & (C < SMA) & (C / C.shift(168) - 1 < 0) & (fl >= 0.0003)
    sig = sig & pd.DataFrame(np.repeat(sett.to_numpy()[:, None], len(COLS), 1), index=H, columns=COLS)
    return run_rule(sig, lambda c, i: trade(c, i, -1, C[c].iat[i] * 1.06, None, 48))


def b3():
    r4 = C / C.shift(4) - 1
    b4 = r4["BTC"]
    trig = (b4 <= -0.03)
    first = trig & ~trig.shift(1).rolling(12, min_periods=1).max().fillna(0).astype(bool)
    mask = base_mask()
    out, busy = [], {c: -1 for c in COLS}
    for i in np.flatnonzero(first.to_numpy()):
        if not BEAR_AT_CLOSE.iat[i]:
            continue
        gap = (r4.iloc[i] - b4.iat[i]).drop("BTC")
        ok = gap[(gap >= 0.02) & mask.iloc[i].drop("BTC")].sort_values(ascending=False)
        for c in ok.index[:10]:
            if i <= busy[c]:
                continue
            t = trade(c, i, -1, C[c].iat[i] * 1.04, None, 12)
            if t:
                busy[c] = t.pop("_j")
                out.append(t)
    return out


def b4():
    """Pair = short alt + long BTC, same notional per leg; pnl in % of one leg; costs on both legs."""
    out = []
    daily = C[C.index.hour == 23]
    dret = daily / daily.shift(1) - 1
    mask = base_mask()
    bh, bc = Hi["BTC"].to_numpy(), C["BTC"].to_numpy()
    for i in np.flatnonzero((H.dayofweek == 6) & (H.hour == 23)):     # Sunday 23:00 bar closes Monday 00:00
        if not BEAR_AT_CLOSE.iat[i]:
            continue
        win = dret[dret.index <= H[i]].tail(60)
        if len(win) < 60:
            continue
        b = win["BTC"]
        beta = win.drop(columns="BTC").apply(lambda s: s.cov(b) / b.var() if s.notna().sum() >= 60 else np.nan)
        el = mask.iloc[i].drop("BTC")
        top = beta[el[el].index].dropna()
        top = top[top >= 1.2].sort_values(ascending=False).head(5)
        for c in top.index:
            ae, be = C[c].iat[i], bc[i]
            ac, ah = C[c].to_numpy(), Hi[c].to_numpy()
            j_end = min(i + 168, len(H) - 1)
            why, j = "time", j_end
            for j in range(i + 1, j_end + 1):
                if np.isnan(ac[j]):
                    j, why = j - 1, "data end"
                    break
                if (bc[j] / be - 1) - (ac[j] / ae - 1) <= -0.08:           # pair stop on hourly closes (exit at that close)
                    why = "stop"
                    break
            gross = (bc[j] / be - 1) - (ac[j] / ae - 1)
            fund = funding_sum(c, T[i], T[j]) - funding_sum("BTC", T[i], T[j])
            out.append({"coin": c, "entry": T[i], "exit": T[j], "side": "pair", "entry_px": ae, "exit_px": ac[j], "why": why,
                        "beta": round(float(top[c]), 2), "btc_leg": bc[j] / be - 1, "alt_leg": -(ac[j] / ae - 1),
                        "gross": gross, "funding": fund, "net": gross + fund - 2 * COST, "net2x": gross + fund - 4 * COST})
    return out


def b5():
    days = bear_day.reindex(pd.date_range(START.normalize(), END.normalize(), freq="D")).fillna(False).astype(bool)
    events = [d for k, d in enumerate(days.index) if k >= 5 and days.iat[k] and not days.iloc[k - 5:k].any()]
    r30 = C / C.shift(720) - 1
    mask = base_mask() & (AGE >= 720)
    out, busy = [], {c: -1 for c in COLS}
    for d in events:
        i = H.get_indexer([d - pd.Timedelta(hours=1)])[0]                # bar 23:00 of the day before, closes at d
        if i < 0:
            continue
        r = r30.iloc[i][mask.iloc[i]].dropna().sort_values(ascending=False)
        for c in r.index[:10]:
            if i <= busy[c]:
                continue
            t = trade(c, i, -1, C[c].iat[i] * 1.12, None, 120)
            if t:
                busy[c] = t.pop("_j")
                out.append(t)
    return out, [str(d.date()) for d in events]


def b6():
    below = (C < SMA).astype(float)
    was_below = below.shift(1).rolling(240, min_periods=240).min() == 1
    reclaim = (C > SMA) & was_below
    mask = base_mask()
    out = []
    for c in COLS:
        cl, sm, hi = C[c].to_numpy(), SMA[c].to_numpy(), Hi[c].to_numpy()
        busy = -1
        for r in np.flatnonzero(reclaim[c].to_numpy()):
            if r <= busy:
                continue
            for k in range(r + 1, min(r + 25, len(H))):
                if cl[k] < sm[k]:
                    if mask[c].iat[k]:
                        t = trade(c, k, -1, np.nanmax(hi[r:k + 1]) * 1.01, None, 72)
                        if t:
                            busy = t.pop("_j")
                            out.append(t)
                    break
    return out


# ------------------------------------------------------------------ report
def stats(tr: pd.DataFrame) -> dict:
    if tr.empty:
        return {"trades": 0, "verdict": "🔴", "why": "no trades"}
    a, b = tr[tr.entry < MID], tr[tr.entry >= MID]
    m = tr.groupby(tr.entry.dt.strftime("%Y-%m")).net.sum()
    s = {"trades": len(tr), "trades_A": len(a), "trades_B": len(b), "win_pct": round(100 * (tr.net > 0).mean(), 1),
         "avg_net": round(100 * tr.net.mean(), 3), "avg_A": round(100 * a.net.mean(), 3) if len(a) else None,
         "avg_B": round(100 * b.net.mean(), 3) if len(b) else None, "avg_net_2x": round(100 * tr.net2x.mean(), 3),
         "avg_funding": round(100 * tr.funding.mean(), 3), "months_pos": f"{int((m > 0).sum())}/{len(m)}",
         "months_pos_pct": round(100 * (m > 0).mean(), 1),
         "years": {str(y): {"trades": int(len(g)), "avg_net": round(100 * g.net.mean(), 3)} for y, g in tr.groupby(tr.entry.dt.year)},
         "exits": tr.why.value_counts().to_dict(),
         "usdt_at_50": round(50 * tr.net.sum(), 1),
         "worst": [{"coin": r.coin, "entry": str(r.entry)[:16], "net_pct": round(100 * r.net, 2)} for r in tr.nsmallest(5, "net").itertuples()]}
    fails = []
    if len(tr) < 150 or len(a) < 50 or len(b) < 50:
        fails.append("trade count")
    if not (len(a) and len(b) and a.net.mean() >= 0.003 and b.net.mean() >= 0.003):
        fails.append("avg net < +0.30% in a half")
    if tr.net2x.mean() <= 0:
        fails.append("loses at 2x costs")
    if (m > 0).mean() < 0.55:
        fails.append("bear months positive < 55%")
    s["verdict"] = "🟠" if not fails else "🔴"
    s["why"] = "passes step 1" if not fails else ", ".join(fails)
    return s


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = {"coins_used": len(COLS), "coins_no_data": NO_DATA,
           "bear_days_pct": round(100 * bear_day[(bear_day.index >= START) & (bear_day.index < END)].mean(), 1)}
    b5_tr, events = b5()
    runs = {"B1 failed_bounce": b1(), "B2 crowded_longs": b2(), "B3 btc_drop_laggards": b3(), "B4 beta_pair": b4(),
            "B5 leaders_catch_down": b5_tr, "B6 failed_reclaim": b6()}
    res["b5_events"] = events
    res["ideas"] = {}
    for name, tr in runs.items():
        df = pd.DataFrame(tr)
        if not df.empty:
            df = df.sort_values("net")
            df.to_csv(OUT / f"trades_{name.split()[0]}.csv", index=False)
        res["ideas"][name] = stats(df)
        print(name, json.dumps({k: v for k, v in res["ideas"][name].items() if k not in ("years", "worst")}, default=str))
    (OUT / "report.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
