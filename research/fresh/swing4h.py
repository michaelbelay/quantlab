r"""Swing test on 4h bars - executes research/fresh/REGISTER_SWING4H_2026-11-12.md. Nothing here is tuned after a run.

    .venv\Scripts\python.exe research\fresh\swing4h.py selftest     synthetic price paths, no market data
    .venv\Scripts\python.exe research\fresh\swing4h.py W1 W2 W3     the registered variants
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache"
MA_BARS, EMA_BARS, HOLD, COOL = 1200, 120, 18, 18     # 200d, 20d, 72h, 72h  (4h bars)
FUND_MIN, STOP, COST, MIN_QV = 0.0001, 0.08, 0.002, 10e6
HALF = pd.Timestamp("2024-05-01", tz="UTC")


def load() -> dict:
    return {k: pd.read_parquet(CACHE / f"panel4h_{k}.parquet") for k in ("C", "H", "L", "QV", "FK", "FP")}


def signals(P: dict, bear_gate: bool) -> pd.DataFrame:
    """The three registered conditions, plus eligibility (200d of history, 10M USDT 24h) and the BTC gate."""
    C = P["C"]
    ma = C.rolling(MA_BARS).mean()
    ema = C.ewm(span=EMA_BARS, adjust=False, min_periods=EMA_BARS).mean()
    sig = (C < ma) & (ma < ma.shift(EMA_BARS)) & (P["FK"] >= FUND_MIN) & (C < ema) & (P["QV"] >= MIN_QV)
    if bear_gate:
        day = C.index.hour == 20                                   # bar 20:00-24:00 -> its close IS the daily close
        d = C.loc[day, "BTC"]
        bear = (d / d.shift(20) - 1) <= 0
        sig = sig & bear.reindex(C.index).ffill().fillna(False).to_numpy()[:, None]
    return sig.fillna(False)


def walk(P: dict, coin: str, i: int, neutral: bool, stop: float | None = STOP) -> dict | None:
    """One trade: short `coin` at the close of bar i (plus long BTC if neutral). Stop first, then the 18-bar hold."""
    C, H, L = P["C"], P["H"], P["L"]
    e = C[coin].iat[i]
    if not np.isfinite(e) or e <= 0:
        return None
    eb = C["BTC"].iat[i]
    stop_px = e * (1 + stop) if stop is not None else np.inf
    last = min(i + HOLD, len(C.index) - 1)
    for j in range(i + 1, last + 1):
        hi = H[coin].iat[j]
        if stop is None:
            hit = False
        elif neutral:                                              # pair stop: coin high with BTC low in the same bar
            worst = (e - H[coin].iat[j]) / e + (L["BTC"].iat[j] - eb) / eb
            hit = worst <= -stop
            px = H[coin].iat[j] if hit else None
        else:
            hit = hi >= stop_px
            px = max(stop_px, C[coin].iat[j - 1]) if hit else None     # a bar opening beyond the stop fills worse
        if hit:
            return _book(P, coin, i, j, e, eb, px, L["BTC"].iat[j] if neutral else None, "stop", neutral, j)
        if j == i + HOLD:
            return _book(P, coin, i, j, e, eb, C[coin].iat[j], C["BTC"].iat[j] if neutral else None, "hold", neutral, j + 1)
    return None


def _book(P, coin, i, j, e, eb, x, xb, reason, neutral, fund_to) -> dict:
    """Net % of notional: price move + real funding - costs. fund_to = first bar NOT counted for funding."""
    C, FP = P["C"], P["FP"]
    gross = (e - x) / e
    f = FP[coin].iloc[i + 1:fund_to].to_numpy()
    p = C[coin].iloc[i + 1:fund_to].to_numpy()
    fund = float(np.nansum(np.where(np.isfinite(p), f * p, 0.0)) / e)          # short receives a positive rate
    cost = COST
    if neutral:
        gross += (xb - eb) / eb
        fb = FP["BTC"].iloc[i + 1:fund_to].to_numpy()
        pb = C["BTC"].iloc[i + 1:fund_to].to_numpy()
        fund -= float(np.nansum(np.where(np.isfinite(pb), fb * pb, 0.0)) / eb)  # the long leg pays
        cost = 2 * COST
    return {"coin": coin, "entry_i": i, "exit_i": j, "time": C.index[i], "exit_time": C.index[j],
            "entry": float(e), "exit": float(x), "gross": float(gross), "fund": fund, "reason": reason,
            "net": float(gross + fund - cost), "net_2x": float(gross + fund - 2 * cost),
            "fund_rate": float(P["FK"][coin].iat[i])}


def run(P: dict, bear_gate: bool, neutral: bool, stop: float | None = STOP) -> pd.DataFrame:
    sig = signals(P, bear_gate)
    out = []
    for coin in sig.columns:
        idx = np.flatnonzero(sig[coin].to_numpy())
        busy = -1
        for i in idx:
            if i <= busy:
                continue
            t = walk(P, coin, int(i), neutral, stop)
            if t is None:
                continue
            out.append(t)
            busy = t["exit_i"] + COOL
    return pd.DataFrame(out)


# ---------------------------------------------------------------- synthetic checks (no market data)
def selftest() -> int:
    n = 60
    idx = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
    def panel(close, high=None, low=None, fund=None, btc=None):
        c = pd.Series(close, index=idx, dtype="float64")
        b = pd.Series(btc if btc is not None else 100.0, index=idx, dtype="float64")
        f = pd.Series(fund if fund is not None else 0.0, index=idx, dtype="float64")
        d = lambda s, o: pd.DataFrame({"X": s, "BTC": o})
        return {"C": d(c, b), "H": d(pd.Series(high, index=idx) if high is not None else c, b * 1.001),
                "L": d(pd.Series(low, index=idx) if low is not None else c, b * 0.999),
                "QV": d(c * 0 + 1e9, b * 0 + 1e9), "FK": d(f, f * 0), "FP": d(f, pd.Series(0.0, index=idx))}
    ok = True
    def check(name, got, want, tol=1e-9):
        nonlocal ok
        good = abs(got - want) < tol
        ok &= good
        print(f"  {'ok  ' if good else 'FAIL'} {name}: {got:.6f} (want {want:.6f})")

    P = panel([100.0] * n)
    t = walk(P, "X", 10, False)
    check("flat price costs exactly the round trip", t["net"], -COST)
    check("flat price exits on the hold", t["exit_i"] - t["entry_i"], HOLD)

    c = [100.0] * n
    for k in range(11, n): c[k] = 95.0
    t = walk(panel(c), "X", 10, False)
    check("5% fall earns 5% minus costs", t["net"], 0.05 - COST)

    c = [100.0] * n; h = list(c)
    h[14] = 109.0                                                  # wick through the 8% stop, close back at 100
    t = walk(panel(c, high=h), "X", 10, False)
    check("wick through the stop fills AT the stop", t["net"], -STOP - COST)
    check("wick exits on that bar", t["exit_i"], 14)

    c = [100.0] * n; h = list(c)
    for k in range(14, n): c[k] = 112.0; h[k] = 113.0              # bar 14 opens at 112 (= close of 13)... gap
    c[13] = 112.0                                                  # close of bar 13 = open of bar 14, beyond the stop
    t = walk(panel(c, high=h), "X", 10, False)
    check("a gap beyond the stop fills at the open, worse than the stop", t["net"], (100 - 112) / 100 - COST)

    f = [0.0] * n
    for k in (12, 14, 16): f[k] = 0.0001                           # three stamps while short at a flat 100
    t = walk(panel([100.0] * n, fund=f), "X", 10, False)
    check("a short is paid the funding it receives", t["net"], 0.0003 - COST, 1e-9)

    c = [100.0] * n
    for k in range(11, n): c[k] = 95.0                             # coin -5%
    b = [100.0] * n
    for k in range(11, n): b[k] = 97.0                             # BTC -3% -> pair +2%
    t = walk(panel(c, btc=b), "X", 10, True)
    check("market-neutral books both legs and pays both costs", t["net"], 0.05 - 0.03 - 2 * COST, 1e-9)
    print("selftest", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    args = sys.argv[1:] or ["selftest"]
    if args == ["selftest"]:
        sys.exit(selftest())


# ---------------------------------------------------------------- report
def report(T: pd.DataFrame, name: str, P: dict, bear_gate: bool) -> dict:
    C = P["C"]
    if T.empty:
        return {"name": name, "trades": 0}
    T = T.copy()
    T["day"] = T["time"].dt.floor("D")
    T["month"] = T["time"].dt.to_period("M").astype(str)
    T["year"] = T["time"].dt.year
    A, B = T[T.time < HALF], T[T.time >= HALF]
    day = C.index.hour == 20
    d = C.loc[day, "BTC"]
    bear_days = int(((d / d.shift(20) - 1) <= 0).sum())
    span_days = (C.index[-1] - C.index[0]).days
    weeks = T["time"].dt.to_period("W").nunique()
    all_weeks = pd.period_range(C.index[0], C.index[-1], freq="W").size
    by_month = T.groupby("month")["net"].sum()
    by_year = T.groupby("year")["net"].sum()
    by_day = T.groupby("day")["net"].sum().sort_values(ascending=False)
    tot = float(T["net"].sum())
    return {
        "name": name, "trades": len(T), "A": len(A), "B": len(B),
        "avg_net_pct": round(100 * T["net"].mean(), 3),
        "avg_A_pct": round(100 * A["net"].mean(), 3) if len(A) else None,
        "avg_B_pct": round(100 * B["net"].mean(), 3) if len(B) else None,
        "avg_2x_pct": round(100 * T["net_2x"].mean(), 3),
        "avg_gross_pct": round(100 * T["gross"].mean(), 3),
        "avg_fund_pct": round(100 * T["fund"].mean(), 3),
        "win_pct": round(100 * (T["net"] > 0).mean(), 1),
        "stops_pct": round(100 * (T["reason"] == "stop").mean(), 1),
        "worst_pct": round(100 * T["net"].min(), 1), "best_pct": round(100 * T["net"].max(), 1),
        "entry_days": int(T["day"].nunique()), "bear_days_in_window": bear_days,
        "entry_days_share_of_bear_days": round(100 * T["day"].nunique() / max(bear_days, 1), 1),
        "trades_per_year": round(len(T) / (span_days / 365.25), 1),
        "trades_per_week": round(len(T) / max(all_weeks, 1), 2),
        "weeks_with_a_trade_pct": round(100 * weeks / max(all_weeks, 1), 1),
        "months_positive_pct": round(100 * (by_month > 0).mean(), 1), "months": len(by_month),
        "by_year_sum_pct": {int(k): round(100 * v, 1) for k, v in by_year.items()},
        "years_positive": int((by_year > 0).sum()), "years": len(by_year),
        "best3_days_share_of_profit_pct": round(100 * by_day.head(3).sum() / tot, 1) if tot > 0 else None,
        "total_sum_pct": round(100 * tot, 1),
    }


def gates(r: dict) -> dict:
    g = {
        "trades >= 150": r["trades"] >= 150,
        "both halves >= 50": r["A"] >= 50 and r["B"] >= 50,
        "avg >= +0.30% in BOTH halves": (r["avg_A_pct"] or -9) >= 0.30 and (r["avg_B_pct"] or -9) >= 0.30,
        "positive at 2x costs": r["avg_2x_pct"] > 0,
        "months positive >= 55%": r["months_positive_pct"] >= 55,
    }
    g["STEP 1"] = all(g.values())
    return g


# ---------------------------------------------------------------- S7 "dip in uptrend" (REGISTER_S7_4H_2026-11-12)
S7_DIP, S7_STOP_SIG, S7_TREND, S7_SIG_BARS = 1.5, 3.0, 60, 180      # frozen on FIT 2021-2023 by s7_pit_fit.py


def s7_sigma(C: pd.DataFrame) -> pd.DataFrame:
    return np.log(C).diff().rolling(S7_SIG_BARS).std() * np.sqrt(6)


def s7_signals(P: dict, top10: bool, qv_min: float = MIN_QV) -> tuple[pd.DataFrame, pd.DataFrame]:
    C = P["C"]
    sig = s7_sigma(C)
    up = C > C.shift(S7_TREND)
    dip = (C / C.shift(6) - 1) <= (-S7_DIP * sig)
    hist = C.rolling(MA_BARS).mean().notna()
    s = up & dip & sig.notna() & (sig > 0) & hist
    if top10:
        month = (P["QV"] / 6).resample("MS").sum()                   # ~ monthly traded value (mean 24h value x bars)
        rank = month.shift(1)
        keep = pd.DataFrame(False, index=C.index, columns=C.columns)
        for m, row in rank.iterrows():
            top = row.dropna().nlargest(10).index
            keep.loc[(keep.index >= m) & (keep.index < m + pd.offsets.MonthBegin(1)), top] = True
        s = s & keep
    else:
        s = s & (P["QV"] >= qv_min)
    return s.fillna(False), sig


def s7_walk(P: dict, coin: str, i: int, sig_v: float) -> dict | None:
    C, L = P["C"], P["L"]
    e = C[coin].iat[i]
    if not np.isfinite(e) or e <= 0 or not np.isfinite(sig_v) or sig_v <= 0:
        return None
    stop_px = e * (1 - S7_STOP_SIG * sig_v)
    last = min(i + HOLD, len(C.index) - 1)
    for j in range(i + 1, last + 1):
        if L[coin].iat[j] <= stop_px:
            op = C[coin].iat[j - 1]
            x = min(stop_px, op) if op < stop_px else stop_px        # a bar opening below the stop fills at the open
            return _s7_book(P, coin, i, j, e, x, "stop", j)
        if j == i + HOLD:
            return _s7_book(P, coin, i, j, e, C[coin].iat[j], "hold", j + 1)
    return None


def _s7_book(P, coin, i, j, e, x, reason, fund_to) -> dict:
    C, FP = P["C"], P["FP"]
    gross = (x - e) / e                                              # LONG
    f = FP[coin].iloc[i + 1:fund_to].to_numpy()
    p = C[coin].iloc[i + 1:fund_to].to_numpy()
    fund = -float(np.nansum(np.where(np.isfinite(p), f * p, 0.0)) / e)   # a long PAYS a positive rate
    return {"coin": coin, "entry_i": i, "exit_i": j, "time": C.index[i], "exit_time": C.index[j],
            "entry": float(e), "exit": float(x), "gross": float(gross), "fund": fund, "reason": reason,
            "net": float(gross + fund - COST), "net_2x": float(gross + fund - 2 * COST),
            "fund_rate": float(P["FK"][coin].iat[i])}


def s7_run(P: dict, top10: bool, qv_min: float = MIN_QV) -> pd.DataFrame:
    s, sig = s7_signals(P, top10, qv_min)
    out = []
    for coin in s.columns:
        idx = np.flatnonzero(s[coin].to_numpy())
        sv = sig[coin].to_numpy()
        busy = -1
        for i in idx:
            if i <= busy:
                continue
            t = s7_walk(P, coin, int(i), float(sv[i]))
            if t is None:
                continue
            out.append(t)
            busy = t["exit_i"] + COOL
    return pd.DataFrame(out)


if __name__ == "__main__" and sys.argv[1:] and sys.argv[1] != "selftest":
    P = load()
    res = {}
    for name in sys.argv[1:]:
        if name.startswith("S7"):
            T = s7_run(P, top10=(name == "S7a"))
            T.to_csv(ROOT / "research" / "fresh" / f"swing4h_{name}_trades.csv", index=False)
            r = report(T, name, P, False); r["gates"] = gates(r) if r["trades"] else {}
            TEST = T[T.time >= pd.Timestamp("2024-01-01", tz="UTC")]
            r["orig_test_window_2024_01_to_2026_09"] = {
                "trades": len(TEST), "avg_net_pct": round(100 * TEST.net.mean(), 3) if len(TEST) else None,
                "pf": round(TEST.net[TEST.net > 0].sum() / abs(TEST.net[TEST.net < 0].sum()), 2) if len(TEST) else None}
            res[name] = r; print(json.dumps(r, indent=1, default=str), flush=True); continue
        bear_gate, neutral, stop = {"W1": (True, False, STOP), "W2": (False, False, STOP), "W3": (True, True, STOP),
                                    "W4": (True, True, None), "W5": (True, False, None)}[name]
        T = run(P, bear_gate, neutral, stop)
        T.to_csv(ROOT / "research" / "fresh" / f"swing4h_{name}_trades.csv", index=False)
        r = report(T, name, P, bear_gate)
        r["gates"] = gates(r) if r["trades"] else {}
        res[name] = r
        print(json.dumps(r, indent=1, default=str), flush=True)
    (ROOT / "research" / "fresh" / "swing4h_results.json").write_text(json.dumps(res, indent=1, default=str))


# ---------------------------------------------------------------- step 2: the 300 USDT account
def account(P: dict, T: pd.DataFrame, slots: int = 6, start: float = 300.0, lev: float = 1.0) -> dict:
    """Walk the bars in order. Deepest dip first when more signal than there are slots. Marked to market every bar."""
    C = P["C"]
    sig = s7_sigma(C)
    T = T.copy()
    T["depth"] = [(C[c].iat[i] / C[c].iat[i - 6] - 1) / sig[c].iat[i] for c, i in zip(T.coin, T.entry_i)]
    by_bar: dict[int, list] = {}
    for r in T.sort_values("depth").itertuples(index=False):        # most negative dip first
        by_bar.setdefault(r.entry_i, []).append(r)
    equity, open_, curve, taken = start, [], [], 0
    for i in range(len(C.index)):
        for t in list(open_):                                        # close what is due
            if t["exit_i"] == i:
                equity += t["stake"] * t["net"]
                open_.remove(t)
        for r in by_bar.get(i, []):
            if len(open_) >= slots or any(o["coin"] == r.coin for o in open_):
                continue
            free = equity - sum(o["stake"] for o in open_)
            stake = max(free / (slots - len(open_)), 0.0) * lev
            if stake < 5.0:
                continue
            open_.append({"coin": r.coin, "stake": stake, "net": r.net, "exit_i": r.exit_i,
                          "entry": r.entry, "i": i})
            taken += 1
        mtm = 0.0
        for o in open_:                                              # mark open trades at this bar's close
            px = C[o["coin"]].iat[i]
            if np.isfinite(px):
                mtm += o["stake"] * ((px - o["entry"]) / o["entry"] - COST)
        curve.append(equity + mtm)
    eq = pd.Series(curve, index=C.index)
    peak = eq.cummax()
    dd = (eq / peak - 1)
    under = (eq < peak).astype(int)
    runs, cur = [], 0
    for u in under:
        cur = cur + 1 if u else 0
        runs.append(cur)
    yr = eq.resample("YE").last()
    return {"slots": slots, "lev": lev, "trades_taken": taken, "of_signals": len(T),
            "final": round(float(eq.iloc[-1]), 1), "max_dd_pct": round(100 * float(dd.min()), 1),
            "longest_under_high_weeks": round(max(runs) * 4 / 24 / 7, 1),
            "year_end": {str(k.year): round(float(v), 1) for k, v in yr.items()},
            "half_A_end": round(float(eq[eq.index < HALF].iloc[-1]), 1)}
