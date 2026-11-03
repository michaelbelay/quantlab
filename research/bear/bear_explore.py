"""Bear short exploration scan: 252 short variants on the trader's 19 coins. Register: REGISTER_BEAR_EXPLORE_2026-11-01.md.

    .venv\\Scripts\\python.exe research\\bear\\bear_explore.py

Scan 2022-01 .. 2026-03 (halves A 2022-23 / B 2024-01..2026-03); held-back 2026-04 .. 2026-09 opened only for the top 5.
Output: research/bear/explore/scan.csv, null.csv, top5.json, trades_<variant>.csv for the top 5.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "explore"
DATA = ROOT / "data" / "market" / "main" / "binance" / "futures"
COINS = ["BTC", "ETH", "ZEC", "SOL", "XRP", "HYPE", "NEAR", "DOGE", "UNI", "BNB", "SUI", "ENA", "QNT", "ARB", "WLD",
         "PUMP", "LINK", "ADA", "TAO"]
START, MIDB, SCAN_END, END = (pd.Timestamp(x, tz="UTC") for x in ("2022-01-01", "2024-01-01", "2026-04-01", "2026-10-01"))
COST = 0.002
H = pd.date_range(START, END - pd.Timedelta(hours=1), freq="h")
T = H + pd.Timedelta(hours=1)
HOLDS, STOPS = (12, 48, 168), (0.03, 0.06, 0.12)
RNG = np.random.default_rng(20261101)


def load(c):
    d = pd.read_feather(DATA / f"{c}_USDT_USDT-1h-futures.feather").drop_duplicates("date").set_index("date").sort_index().reindex(H)
    f = pd.read_feather(DATA / f"{c}_USDT_USDT-1h-funding_rate.feather").drop_duplicates("date").set_index("date").funding_rate
    return d, f


RAW = {c: load(c) for c in COINS}
O, Hi, Lo, C, V = (pd.DataFrame({c: RAW[c][0][k] for c in COINS}) for k in ("open", "high", "low", "close", "volume"))
FUND_AT = pd.DataFrame({c: RAW[c][1].reindex(T).to_numpy() for c in COINS}, index=H)       # funding settled at bar close
CUMF = FUND_AT.fillna(0).cumsum()
ELIG = ((C * V).rolling(24, min_periods=24).sum() >= 1e7) & C.notna()

btc = C["BTC"]
dc = btc[btc.index.hour == 23]
dc.index = dc.index.normalize() + pd.Timedelta(days=1)
bear_day = dc / dc.shift(20) - 1 <= 0
BEAR = pd.Series(H.normalize().map(bear_day).fillna(False).astype(bool).to_numpy(), index=H)
BEAR_CLOSE = BEAR.shift(-1, fill_value=False)
BASE = ELIG & pd.DataFrame(np.repeat(BEAR_CLOSE.to_numpy()[:, None], len(COINS), 1), index=H, columns=COINS)


def ema(n):
    return C.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(n=14):
    d = C.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def entries() -> dict[str, pd.DataFrame]:
    e480, r = ema(480), rsi()
    hour = pd.DataFrame(np.repeat(H.hour.to_numpy()[:, None], len(COINS), 1), index=H, columns=COINS)
    close_hour = (hour + 1) % 24
    r24, r1, r168 = C / C.shift(24) - 1, C / C.shift(1) - 1, C / C.shift(168) - 1
    S = {}
    for n in (24, 72, 168, 480):
        e = ema(n)
        S[f"T_ema{n}"] = (C < e) & (C.shift(1) >= e.shift(1))
    for n in (24, 72, 168, 480):
        S[f"K_low{n}"] = C < Lo.shift(1).rolling(n, min_periods=n).min()
    for x in (60, 70, 80):
        S[f"R_rsi{x}"] = (r < x) & (r.shift(1) >= x) & (C < e480)
    rel = r168.sub(r168["BTC"], axis=0)
    for x in (0.05, 0.10, 0.20):
        m = (hour == 23) & (rel <= -x)
        m["BTC"] = False
        S[f"W_rel{int(x * 100)}"] = m
    for f in (0.0001, 0.0002, 0.0005):
        S[f"U_fund{f * 100:.2f}"] = FUND_AT.notna() & (FUND_AT >= f) & (C < e480)
    for h in (0, 4, 8, 12, 16, 20):
        S[f"D_hour{h:02d}"] = close_hour == h
    for x in (0.05, 0.10, 0.20):
        S[f"P_pump{int(x * 100)}"] = (r24 >= x) & ~(r24.shift(1) >= x)
    vavg = V.shift(1).rolling(24, min_periods=24).mean()
    for y in (0.02, 0.04):
        S[f"V_sell{int(y * 100)}"] = (r1 <= -y) & (V >= 3 * vavg)
    return {k: (v & BASE).fillna(False) for k, v in S.items()}


ARR = {c: (C[c].to_numpy(), Hi[c].to_numpy(), CUMF[c].to_numpy()) for c in COINS}


def short(c, i, hold, stop):
    cl, hi, cf = ARR[c]
    e = cl[i]
    j_end = min(i + hold, len(H) - 1)
    seg_h, seg_c = hi[i + 1:j_end + 1], cl[i + 1:j_end + 1]
    nan = np.flatnonzero(np.isnan(seg_c))
    if len(nan):
        seg_h, seg_c = seg_h[:nan[0]], seg_c[:nan[0]]
        if not len(seg_c):
            return None
    sp = e * (1 + stop)
    hit = np.flatnonzero(seg_h >= sp)
    if len(hit):
        j, px = i + 1 + hit[0], sp
    else:
        j, px = i + len(seg_c), seg_c[-1]
    gross = -(px / e - 1)
    fund = cf[j] - cf[i]
    return j, gross + fund - COST, gross + fund - 2 * COST


def run(sig: pd.DataFrame, hold, stop, lo=START, hi=SCAN_END):
    rows = []
    ok = (H >= lo) & (H < hi)
    for c in COINS:
        busy = -1
        for i in np.flatnonzero(sig[c].to_numpy() & ok):
            if i <= busy:
                continue
            t = short(c, i, hold, stop)
            if t:
                busy = t[0]
                rows.append((c, H[i], t[1], t[2]))
    return pd.DataFrame(rows, columns=["coin", "entry", "net", "net2x"])


def score(tr: pd.DataFrame) -> dict:
    if tr.empty:
        return {"trades": 0, "pass": False}
    a, b = tr[tr.entry < MIDB], tr[tr.entry >= MIDB]
    m = tr.groupby(tr.entry.dt.strftime("%Y-%m")).net.sum()
    s = {"trades": len(tr), "trades_A": len(a), "trades_B": len(b), "avg": 100 * tr.net.mean(),
         "avg_A": 100 * a.net.mean() if len(a) else np.nan, "avg_B": 100 * b.net.mean() if len(b) else np.nan,
         "avg_2x": 100 * tr.net2x.mean(), "months_pos_pct": 100 * (m > 0).mean(), "win_pct": 100 * (tr.net > 0).mean()}
    s["pass"] = bool(len(tr) >= 100 and len(a) >= 30 and len(b) >= 30 and s["avg_A"] >= 0.30 and s["avg_B"] >= 0.30
                     and s["avg_2x"] > 0 and s["months_pos_pct"] >= 55)
    s["weaker_half"] = min(s["avg_A"], s["avg_B"])
    return s


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    S = entries()
    pool = BASE & pd.DataFrame(np.repeat(((H >= START) & (H < SCAN_END))[:, None], len(COINS), 1), index=H, columns=COINS)
    pool_idx = np.argwhere(pool.to_numpy())
    rows, null = [], []
    for name, sig in S.items():
        for hold in HOLDS:
            for stop in STOPS:
                tr = run(sig, hold, stop)
                rows.append({"variant": f"{name}|h{hold}|s{int(stop * 100)}", "family": name[0], "entry": name,
                             "hold": hold, "stop": stop, **score(tr)})
                # null: same number of random bear-day entries, same exits
                n = max(len(tr), 1)
                pick = pool_idx[RNG.choice(len(pool_idx), size=n, replace=False)]
                nr = [(COINS[k], H[i], *short(COINS[k], i, hold, stop)[1:]) for i, k in pick if short(COINS[k], i, hold, stop)]
                null.append({"variant": rows[-1]["variant"], **score(pd.DataFrame(nr, columns=["coin", "entry", "net", "net2x"]))})
    scan = pd.DataFrame(rows).sort_values("weaker_half", ascending=False)
    scan.to_csv(OUT / "scan.csv", index=False)
    pd.DataFrame(null).to_csv(OUT / "null.csv", index=False)
    surv = scan[scan["pass"]]
    top = surv.drop_duplicates("family").head(5)
    held = {}
    for r in top.itertuples():
        tr = run(S[r.entry], r.hold, r.stop, SCAN_END, END)
        full = pd.concat([run(S[r.entry], r.hold, r.stop), tr])
        full.sort_values("net").to_csv(OUT / f"trades_{r.variant.replace('|', '_')}.csv", index=False)
        held[r.variant] = {"trades": len(tr), "avg": round(100 * tr.net.mean(), 3) if len(tr) else None,
                           "avg_2x": round(100 * tr.net2x.mean(), 3) if len(tr) else None,
                           "pass": bool(len(tr) >= 20 and tr.net2x.mean() > 0),
                           "worst": [(x.coin, str(x.entry)[:10], round(100 * x.net, 2)) for x in tr.nsmallest(3, "net").itertuples()]}
    nl = pd.DataFrame(null)
    out = {"variants": len(scan), "passed_scan": int(scan["pass"].sum()), "null_passed": int(nl["pass"].sum()),
           "null_avg_of_avgs": round(nl["avg"].mean(), 3), "real_avg_of_avgs": round(scan["avg"].mean(), 3),
           "top5": top.round(3).to_dict("records"), "held_back": held,
           "best_10_by_weaker_half": scan.head(10).round(3).to_dict("records"),
           "family_best": scan.groupby("family").head(1).round(3).to_dict("records")}
    (OUT / "top5.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("variants", "passed_scan", "null_passed", "null_avg_of_avgs", "real_avg_of_avgs")}))
    print("held back:", json.dumps(held, default=str))
    print(scan.head(12)[["variant", "trades", "avg", "avg_A", "avg_B", "avg_2x", "months_pos_pct", "pass"]].round(3).to_string())


if __name__ == "__main__":
    main()
