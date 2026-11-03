"""Bear ideas batch 3, order flow (F1-F5), step 1 signal test. Rules: RULES_BEAR.md, REGISTER_BEAR_FLOW_2026-11-01.md.

    .venv\\Scripts\\python.exe research\\bear\\bear_flow.py

Same candles, bear flag, costs, funding and gates as bear_ideas.py (imported). Output: research/bear/batch3/.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import bear_ideas as B

H = B.H
OUT = B.HERE / "batch3"
FLOW = B.ROOT / "data" / "market" / "flow"
COLS = [c for c in B.COLS if (FLOW / f"{c}.feather").exists()]
C, Hi, SMA = B.C[COLS], B.Hi[COLS], B.SMA[COLS]
MASK = B.base_mask()[COLS]


def flow(c: str) -> pd.DataFrame:
    d = pd.read_feather(FLOW / f"{c}.feather").drop_duplicates("date").set_index("date").sort_index().reindex(H)
    return d[["quote_volume", "taker_buy_quote"]]


F = {c: flow(c) for c in COLS}
QV = pd.DataFrame({c: F[c].quote_volume for c in COLS})
BQ = pd.DataFrame({c: F[c].taker_buy_quote for c in COLS})


def share(n: int) -> pd.DataFrame:
    return BQ.rolling(n, min_periods=n).sum() / QV.rolling(n, min_periods=n).sum()


def rank(x: pd.DataFrame | pd.Series, n: int = 720):
    """Position of the current value among the previous n values (0 lowest .. 1 highest)."""
    return x.rolling(n + 1, min_periods=n + 1).rank(pct=True)


BS24, BS168 = share(24), share(168)
R24, R168 = rank(BS24), rank(BS168)
RET24, RET168 = C / C.shift(24) - 1, C / C.shift(168) - 1
DELTA72 = (2 * BQ - QV).rolling(72, min_periods=72).sum()


def run(sig: pd.DataFrame, stop_fn, hold: int, gap: int = 0) -> list[dict]:
    out = []
    for c in COLS:
        busy, last = -1, -10 ** 9
        for i in np.flatnonzero(sig[c].fillna(False).to_numpy()):
            if i <= busy or i - last < gap:
                continue
            t = B.trade(c, i, -1, stop_fn(c, i), None, hold)
            if t:
                busy, last = t.pop("_j"), i
                out.append(t)
    return out


def f1():
    return run(MASK & (C < SMA) & (RET24 >= 0.05) & (R24 <= 0.30), lambda c, i: C[c].iat[i] * 1.08, 48, gap=24)


def f2():
    return run(MASK & (R24 >= 0.90) & (RET24 <= 0), lambda c, i: C[c].iat[i] * 1.06, 48)


def f3():
    h72 = Hi.rolling(72).max()
    sig = MASK & (C >= C.rolling(72).max()) & (DELTA72 < 0)
    return run(sig, lambda c, i: h72[c].iat[i] * 1.02, 72)


def f4():
    vol24 = QV.rolling(24, min_periods=24).sum()
    top = vol24.rank(axis=1, ascending=False) <= 50
    mk = BQ.rolling(24, min_periods=24).sum()[top].sum(axis=1) / vol24[top].sum(axis=1)
    mr = rank(mk)
    trig = (mr >= 0.90) & B.BEAR_AT_CLOSE
    out, busy, last = [], {c: -1 for c in COLS}, -10 ** 9
    for i in np.flatnonzero(trig.to_numpy()):
        if i - last < 24:
            continue
        last = i
        s = BS24.iloc[i][MASK.iloc[i]].dropna().sort_values(ascending=False)
        for c in s.index[:10]:
            if i > busy[c]:
                t = B.trade(c, i, -1, C[c].iat[i] * 1.08, None, 48)
                if t:
                    busy[c] = t.pop("_j")
                    out.append(t)
    return out


def f5():
    return run(MASK & (R168 <= 0.10) & (C < SMA) & (RET168 < 0), lambda c, i: C[c].iat[i] * 1.08, 72, gap=72)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    runs = {"F1 covering_rally": f1(), "F2 absorbed_buying": f2(), "F3 delta_divergence": f3(),
            "F4 market_euphoria": f4(), "F5 persistent_selling": f5()}
    res = {"coins_used": len(COLS), "ideas": {}}
    for name, tr in runs.items():
        df = pd.DataFrame(tr)
        if not df.empty:
            df = df.sort_values("net")
            df.to_csv(OUT / f"trades_{name.split()[0]}.csv", index=False)
        s = B.stats(df)
        if not df.empty:
            cap = df.net.clip(lower=-1)
            s["below_minus_100"] = int((df.net < -1).sum())
            s["avg_net_capped"] = round(100 * cap.mean(), 3)
        res["ideas"][name] = s
        print(name, json.dumps({k: v for k, v in s.items() if k not in ("years", "worst")}, default=str))
    (OUT / "report.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
