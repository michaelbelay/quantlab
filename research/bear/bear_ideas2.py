"""Bear ideas batch 2 (C1-C5), step 1 signal test. Rules: RULES_BEAR.md, REGISTER_BEAR_IDEAS_2026-11-01_batch2.md.

    .venv\\Scripts\\python.exe research\\bear\\bear_ideas2.py

Same data, bear flag, costs, funding and gates as bear_ideas.py (imported). Output: research/bear/batch2/.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import bear_ideas as B

C, Hi, Lo, H, T = B.C, B.Hi, B.Lo, B.H, B.T
MASK = B.base_mask()
OUT = B.HERE / "batch2"
DAILY = np.flatnonzero(H.hour == 23)                       # bars whose close is the daily close


def walk(c: str, i: int, stop0: float, max_h: int, daily_exit=None, trail=None) -> dict | None:
    """Short from close of bar i. Every hour: stop first (high >= stop). At daily closes: optional exit test and trailing
    stop update. Ends at max_h hours."""
    hi, cl = Hi[c].to_numpy(), C[c].to_numpy()
    e, stop, n = cl[i], stop0, len(H)
    j_end = min(i + max_h, n - 1)
    px, why, j = cl[j_end], "time", j_end
    low_close = e
    for j in range(i + 1, j_end + 1):
        if np.isnan(cl[j]):
            j -= 1
            px, why = cl[j], "data end"
            break
        if hi[j] >= stop:
            px, why = stop, "stop"
            break
        if H[j].hour == 23:
            if daily_exit is not None and daily_exit(j):
                px, why = cl[j], "rule exit"
                break
            if trail is not None:
                low_close = min(low_close, cl[j])
                stop = min(stop, trail(j, low_close))
    else:
        j = j_end
    gross = -(px / e - 1)
    fund = B.funding_sum(c, T[i], T[j])
    return {"coin": c, "entry": T[i], "exit": T[j], "side": "short", "entry_px": e, "exit_px": px, "why": why,
            "gross": gross, "funding": fund, "net": gross + fund - B.COST, "net2x": gross + fund - 2 * B.COST, "_j": j}


def keep(out, t, busy, c):
    if t:
        busy[c] = t.pop("_j")
        out.append(t)


def c1():
    r20 = C / C.shift(480) - 1
    out, busy = [], {}
    for c in ("BTC", "ETH", "BNB"):
        busy[c] = -1
        rc = r20[c].to_numpy()
        for i in DAILY:
            if i <= busy[c] or not (rc[i] <= 0 and MASK[c].iat[i]):
                continue
            keep(out, walk(c, i, C[c].iat[i] * 1.10, 720,
                           daily_exit=lambda j, rc=rc: rc[j] > 0 or not B.BEAR_AT_CLOSE.iat[j]), busy, c)
    return out


def c2():
    dC = C.iloc[DAILY]
    # daily high/low over the whole UTC day (24 bars ending at the 23:00 bar)
    dH = Hi.rolling(24).max().iloc[DAILY]
    dL = Lo.rolling(24).min().iloc[DAILY]
    pc = dC.shift(1)
    tr = pd.concat([dH - dL, (dH - pc).abs(), (dL - pc).abs()]).groupby(level=0).max()
    atr = tr.rolling(14, min_periods=14).mean()
    brk = dC < dL.shift(1).rolling(20, min_periods=20).min()
    atr_h = atr.reindex(H)                                  # value only at daily bars
    out = []
    for c in B.COLS:
        busy = -1
        ah = atr_h[c].to_numpy()
        for i in DAILY[np.flatnonzero(brk[c].to_numpy())]:
            if i <= busy or not MASK[c].iat[i] or np.isnan(ah[i]):
                continue
            t = walk(c, i, C[c].iat[i] + 2 * ah[i], 720, trail=lambda j, lc, ah=ah: lc + 2 * ah[j] if not np.isnan(ah[j]) else np.inf)
            if t:
                busy = t.pop("_j")
                out.append(t)
    return out


def c3():
    b = C["BTC"]
    r72 = C / C.shift(72) - 1
    avg = b.rolling(24).mean()
    trig = (b < avg) & (b.shift(1) >= avg.shift(1)) & (r72["BTC"].rolling(24).max() >= 0.05)
    out, busy, last = [], {c: -1 for c in B.COLS}, -10 ** 9
    for i in np.flatnonzero(trig.to_numpy()):
        if i - last < 72 or not B.BEAR_AT_CLOSE.iat[i]:
            continue
        last = i
        r = r72.iloc[i].drop("BTC")[MASK.iloc[i].drop("BTC")].dropna().sort_values(ascending=False)
        for c in r.index[:10]:
            if i > busy[c]:
                keep(out, B.trade(c, i, -1, C[c].iat[i] * 1.08, None, 72), busy, c)
    return out


def c4():
    out, busy = [], {c: -1 for c in B.COLS}
    for i in np.flatnonzero((H.dayofweek == 6) & (H.hour == 23)):
        if i < 48 or not B.BEAR_AT_CLOSE.iat[i]:
            continue
        wk = C.iloc[i] / C.iloc[i - 48] - 1                       # Saturday 00:00 -> Monday 00:00
        if not wk["BTC"] < 0.03:
            continue
        for c in wk.drop("BTC")[(wk.drop("BTC") >= 0.08) & MASK.iloc[i].drop("BTC")].index:
            if i > busy[c]:
                keep(out, B.trade(c, i, -1, C[c].iat[i] * 1.08, None, 72), busy, c)
    return out


def c5():
    out, busy = [], {"BTC": -1, "ETH": -1}
    for i in np.flatnonzero(H.hour == 12):                         # 12:00 bar closes 13:00 UTC; exit after 8 bars = 21:00
        for c in ("BTC", "ETH"):
            if i > busy[c] and B.BEAR_AT_CLOSE.iat[i] and MASK[c].iat[i]:
                keep(out, B.trade(c, i, -1, C[c].iat[i] * 1.03, None, 8), busy, c)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    runs = {"C1 majors_trend_short": c1(), "C2 breakdown_trail": c2(), "C3 market_rally_fail": c3(),
            "C4 weekend_pump_fade": c4(), "C5 session_short": c5()}
    res = {"coins_used": len(B.COLS), "ideas": {}}
    for name, tr in runs.items():
        df = pd.DataFrame(tr)
        if not df.empty:
            df = df.sort_values("net")
            df.to_csv(OUT / f"trades_{name.split()[0]}.csv", index=False)
        res["ideas"][name] = B.stats(df)
        print(name, json.dumps({k: v for k, v in res["ideas"][name].items() if k not in ("years", "worst")}, default=str))
    (OUT / "report.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
