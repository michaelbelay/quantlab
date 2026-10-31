r"""C40 = C32 (funding-crowding short, unchanged) + MajorsTrend regime gate: trade only while BTC's 20-day return
at the last completed UTC daily close is <= 0 (MajorsTrend's BTC leg is out). Registered in FAMILIES_C.md (7ed595c).

    .venv\Scripts\python.exe -m quant.run_c40

1h, all 413 coins, 300 USDT book (20 slots), fee 0.05% + slippage 0.05% per side, funding, next-bar entry.
Judges (fixed before running): DEV Protocol C gates + mechanism check, then RECENT PF > 1.0 and profit.
VALID is the diagnosis source -> reported as "seen", never used for the decision.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from strategies.families_c import c14_like

from . import trades as T
from .bars import bars, universe_1h
from .book import metrics, replay
from .eval_c import PERIODS, mins
from .paths import RUNS

WINDOWS = {"DEV": ("2021-01-01", "2024-07-01"), "VALID (seen)": ("2024-07-01", "2026-03-26"),
           "RECENT": ("2026-03-26", "2026-09-26")}
HALF_YEARS = [(f"{y}H{h}", f"{y}-{'01' if h == 1 else '07'}-01", f"{y + (h == 2)}-{'07' if h == 1 else '01'}-01")
              for y in range(2022, 2027) for h in (1, 2)][1:9]                      # 2022H2 .. 2026H1
REPS = 100


def btc_gate() -> pd.Series:
    """True while BTC 20d return <= 0, indexed by the time the value becomes known (next UTC midnight)."""
    b = bars("BTC", "1h").set_index("date")["close"]
    d = b.resample("1D").last().dropna()
    r20 = d / d.shift(20) - 1
    known = pd.Series((r20 <= 0).to_numpy(), index=r20.index + pd.Timedelta(days=1))
    return known[r20.notna().to_numpy()]


def gate_at(gate: pd.Series, times: pd.Series) -> np.ndarray:
    """Gate value known at each time (signal bar close = bar open + 1h). Unknown -> False (no trade)."""
    idx = gate.index.searchsorted(pd.DatetimeIndex(times), side="right") - 1
    ok = idx >= 0
    out = np.zeros(len(times), bool)
    out[ok] = gate.to_numpy()[idx[ok]]
    return out


def book(t: pd.DataFrame, mn: dict, periods) -> dict:
    if not len(t):
        return {"trades": 0}
    bt, curve = replay(t.reset_index(drop=True), mn)
    m = metrics(bt, curve, periods)
    t2 = t.copy()
    t2["ret"] = t2["ret"] - 2 * (T.FEE + T.SLIP) - np.where(t2["reason"] == "stop", T.STOP_EXTRA, 0.0)
    bt2, c2 = replay(t2.reset_index(drop=True), mn)
    m2 = metrics(bt2, c2, periods)
    m["x2"] = {k: m2.get(k) for k in ("final", "pf", "max_dd_pct")}
    return m


def pf(r: pd.Series) -> float:
    return round(float(r[r > 0].sum() / max(1e-9, -r[r < 0].sum())), 3)


def main() -> int:
    gate = btc_gate()
    rng = np.random.default_rng(40)
    rows = {"C32": [], "C40": []}
    twin = {w: np.zeros(REPS) for w in WINDOWS}
    for coin in universe_1h():
        df = bars(coin, "1h")
        if len(df) < 40 * 24:
            continue
        a = T.atr(df)
        _, ss, ex = c14_like(df, a, {"bpd": 24, "tf": "1h"}, 2.5)            # C32, unchanged
        down = gate_at(gate, df["date"] + pd.Timedelta(hours=1))
        z = np.zeros_like(ss)
        o, c, d = df["open"].to_numpy(), df["close"].to_numpy(), df["date"]
        for fid, sig in (("C32", ss), ("C40", ss & down)):
            tr = T.simulate(df, z, sig, ex, a, 24)
            for t in tr:
                t["coin"] = coin
                t["btc_down"] = bool(down[t["entry_i"] - 1])
                rows[fid].append({k: t[k] for k in ("coin", "side", "entry_t", "exit_t", "ret", "mae", "reason",
                                                    "bars", "btc_down")})
            if fid != "C40":
                continue
            for w, (s0, s1) in WINDOWS.items():                                 # random-timing twins of C40
                lo = int(d.searchsorted(pd.Timestamp(s0, tz="UTC")))
                hi = int(d.searchsorted(pd.Timestamp(s1, tz="UTC"))) - 1
                for t in (t for t in tr if lo <= t["entry_i"] <= hi):
                    b = t["bars"]
                    if hi - b + 1 <= lo:
                        continue
                    e = lo + (rng.random(REPS) * (hi - b + 1 - lo)).astype(int)
                    x = np.minimum(e + b - 1, len(c) - 1)
                    with np.errstate(invalid="ignore", divide="ignore"):
                        twin[w] += np.nan_to_num(t["side"] * (c[x] / o[e] - 1) - 2 * (T.FEE + T.SLIP))
    allt = {}
    for fid, r in rows.items():
        x = pd.DataFrame(r)
        for col in ("entry_t", "exit_t"):
            x[col] = pd.to_datetime(x[col], utc=True)
        allt[fid] = x
    mn = mins()
    per = {"DEV": PERIODS["1h"]["dev"], "VALID (seen)": PERIODS["1h"]["valid"],
           "RECENT": [("2026Q2", "2026-03-26", "2026-07-01"), ("2026Q3", "2026-07-01", "2026-09-26")]}
    out = {"rule": "C32 short AND BTC 20d return <= 0 at last daily close", "windows": {}}
    for w, (s0, s1) in WINDOWS.items():
        res = {}
        for fid, x in allt.items():
            t = x[(x["entry_t"] >= pd.Timestamp(s0, tz="UTC")) & (x["entry_t"] < pd.Timestamp(s1, tz="UTC"))]
            res[fid] = book(t, mn, per[w])
            if fid == "C32" and len(t):                                         # mechanism check
                res["C32_by_regime"] = {
                    "btc_up": {"n": int((~t["btc_down"]).sum()), "pf_per_trade": pf(t.loc[~t["btc_down"], "ret"]),
                               "mean_pct": round(float(t.loc[~t["btc_down"], "ret"].mean() * 100), 3)},
                    "btc_down": {"n": int(t["btc_down"].sum()), "pf_per_trade": pf(t.loc[t["btc_down"], "ret"]),
                                 "mean_pct": round(float(t.loc[t["btc_down"], "ret"].mean() * 100), 3)}}
            if fid == "C40":
                res["C40_twin_pct"] = float((twin[w] < t["ret"].sum()).mean() * 100) if len(t) else None
        out["windows"][w] = res
    hy = {}
    x = allt["C40"]
    for name, a_, b_ in HALF_YEARS:
        t = x[(x["entry_t"] >= pd.Timestamp(a_, tz="UTC")) & (x["entry_t"] < pd.Timestamp(b_, tz="UTC"))]
        hy[name] = {"trades": int(len(t)), "sum_ret_pct": round(float(t["ret"].sum() * 100), 2)}
    out["walk_forward_half_years"] = hy
    out["walk_forward_positive"] = sum(v["sum_ret_pct"] > 0 for v in hy.values())

    dv, rc = out["windows"]["DEV"], out["windows"]["RECENT"]
    m = dv["C40"]
    g1 = {"≥200 trades": m.get("trades", 0) >= 200, "PF ≥ 1.15": m.get("pf", 0) >= 1.15,
          "PF ≥ 1.0 at 2x costs": (m.get("x2") or {}).get("pf", 0) >= 1.0, "DD ≤ 35%": m.get("max_dd_pct", 100) <= 35,
          "≥3 of 4 periods positive": m.get("periods_positive", 0) >= 3,
          "beats 95% of random twins": (dv.get("C40_twin_pct") or 0) >= 95,
          "top coin ≤ 20% of profit": (m.get("top_coin_share") or 1) <= 0.20,
          "mechanism: C32 PF lower when BTC up": dv["C32_by_regime"]["btc_up"]["pf_per_trade"]
          < dv["C32_by_regime"]["btc_down"]["pf_per_trade"]}
    r = rc["C40"]
    g2 = {"RECENT PF > 1.0": r.get("pf", 0) > 1.0, "RECENT profit": r.get("final", 0) > 300}
    out["gates_dev"], out["gates_recent"] = g1, g2
    out["decision"] = "FORWARD PAPER TEST" if all(g1.values()) and all(g2.values()) else "KILL"
    (RUNS / "C40_trend_gate.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")

    print("| Window | Family | Trades | PF | PF x2 costs | 300 USDT → | Max DD | Periods + | Twins |")
    print("|---|---|---|---|---|---|---|---|---|")
    for w, res in out["windows"].items():
        for fid in ("C32", "C40"):
            m = res[fid]
            tw = f"p{res['C40_twin_pct']:.0f}" if fid == "C40" and res.get("C40_twin_pct") is not None else ""
            print(f"| {w} | {fid} | {m.get('trades', 0)} | {m.get('pf')} | {(m.get('x2') or {}).get('pf')} | "
                  f"{m.get('final')} | {m.get('max_dd_pct')}% | {m.get('periods_positive')}/{len(m.get('periods', {}))} "
                  f"{m.get('periods')} | {tw} |")
        if "C32_by_regime" in res:
            print(f"|   | C32 by regime | {res['C32_by_regime']} |")
    print("\nWalk-forward C40:", out["walk_forward_positive"], "/ 8 positive", hy)
    print("DEV gates:", g1)
    print("RECENT gates:", g2)
    print("DECISION:", out["decision"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
