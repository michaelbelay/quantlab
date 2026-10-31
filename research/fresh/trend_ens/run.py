"""Trend ensemble (Zarattini/Pagani/Barbon rules) - variants A1/A2/A3. Rule: ../REGISTER_TREND_ENS_2026-10-25.md.

    .venv\\Scripts\\python.exe research\\fresh\\trend_ens\\run.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
LB = [5, 10, 20, 30, 60, 90, 150, 250, 360]
COST, VT, CAP, TOPN, EQ0 = 0.001, 0.25, 2.0, 20, 300.0
DIV = True   # 2026-10-25 B variants (see register); False reproduces A1-A3
START, END = pd.Timestamp("2021-01-01", tz="UTC"), pd.Timestamp("2026-10-25", tz="UTC")


def panel():
    C, Q = {}, {}
    for f in sorted((HERE / "data").glob("*.feather")):
        d = pd.read_feather(f).set_index("date")
        if len(d) > 30:
            C[f.stem], Q[f.stem] = d["close"], d["qv"]
    return pd.DataFrame(C).sort_index(), pd.DataFrame(Q).sort_index()


def states(c: np.ndarray, short: bool) -> np.ndarray:
    """(T, 9) array of +1/-1/0 per lookback, decided at each close."""
    T = len(c)
    out = np.zeros((T, len(LB)))
    s = pd.Series(c)
    for k, n in enumerate(LB):
        hi_prev, lo_prev = s.shift(1).rolling(n).max().to_numpy(), s.shift(1).rolling(n).min().to_numpy()
        mid = ((s.rolling(n).max() + s.rolling(n).min()) / 2).to_numpy()
        pos, stop = 0, np.nan
        for t in range(T):
            x = c[t]
            if np.isnan(x) or np.isnan(hi_prev[t]):
                pos = 0
                continue
            if pos == 1:
                stop = max(stop, mid[t])
                if x < stop:
                    pos = 0
            elif pos == -1:
                stop = min(stop, mid[t])
                if x > stop:
                    pos = 0
            if pos == 0:
                if x > hi_prev[t]:
                    pos, stop = 1, mid[t]
                elif short and x < lo_prev[t]:
                    pos, stop = -1, mid[t]
            out[t, k] = pos
    return out


def run(C: pd.DataFrame, Q: pd.DataFrame, short: bool, coins: list[str] | None):
    if coins:
        C, Q = C[coins], Q[coins]
    idx, names = C.index, list(C.columns)
    c = C.to_numpy()
    R = C.pct_change().to_numpy()
    vol = (C.pct_change().rolling(90).std() * np.sqrt(365)).to_numpy()
    age = C.notna().cumsum().to_numpy()
    S = np.stack([states(c[:, j], short) for j in range(len(names))], axis=1)       # (T, N, 9)
    # universe: monthly top-N by 30-day median quote volume, listed >= 365 days
    uni = np.zeros(c.shape, bool)
    medq = Q.rolling(30).median().to_numpy()
    cur = np.zeros(len(names), bool)
    for t in range(len(idx)):
        if t == 0 or idx[t].month != idx[t - 1].month:
            ok = (age[t] >= 365) & ~np.isnan(medq[t])
            cur = np.zeros(len(names), bool)
            if coins:
                cur = ok
            else:
                order = np.argsort(-np.where(ok, medq[t], -1))
                cur[[i for i in order[:TOPN] if ok[i]]] = True
        uni[t] = cur
    scale = np.where(vol > 0, VT / vol, 0.0)
    part = S / len(LB) * np.nan_to_num(scale)[:, :, None] * uni[:, :, None]          # per lookback weight
    if DIV:                                    # B variants: equal-weight average of single-coin strategies
        part = part / np.maximum(uni.sum(axis=1), 1)[:, None, None]
    w = part.sum(axis=2)
    gross = np.abs(w).sum(axis=1)
    f = np.where(gross > CAP, CAP / np.maximum(gross, 1e-12), 1.0)
    w, part = w * f[:, None], part * f[:, None, None]
    Rn = np.nan_to_num(np.vstack([R[1:], np.zeros((1, R.shape[1]))]))              # next-day return
    turn = np.abs(np.diff(np.vstack([np.zeros((1, w.shape[1])), w]), axis=0)).sum(axis=1)
    port = (w * Rn).sum(axis=1) - COST * turn
    s = pd.Series(port, index=idx).shift(1).fillna(0.0)                                # realised the next day
    m = (idx >= START) & (idx < END)
    s = s[m]
    eq = EQ0 * (1 + s).cumprod()
    # per-position (lookback episode) stats, USDT at the equity of the day
    eqv = pd.Series(EQ0 * (1 + pd.Series(port, index=idx).where(m, 0.0)).cumprod().shift(1).fillna(EQ0).to_numpy(), index=idx)
    contrib = part * Rn[:, :, None] * eqv.to_numpy()[:, None, None] - COST * np.abs(np.diff(
        np.concatenate([np.zeros((1,) + part.shape[1:]), part]), axis=0)) * eqv.to_numpy()[:, None, None]
    trades = []
    tm = np.flatnonzero(m)
    for j in range(len(names)):
        for k in range(len(LB)):
            on = part[:, j, k] != 0
            t, T = tm[0], tm[-1]
            while t <= T:
                if on[t]:
                    a = t
                    while t + 1 <= T and on[t + 1] and np.sign(part[t + 1, j, k]) == np.sign(part[a, j, k]):
                        t += 1
                    pnl = contrib[a:t + 1, j, k].sum()
                    cum = np.cumsum(contrib[a:t + 1, j, k])
                    trades.append((names[j], LB[k], int(np.sign(part[a, j, k])), idx[a], t - a + 1, pnl, int((cum < 0).sum())))
                t += 1
    Tr = pd.DataFrame(trades, columns=["coin", "lb", "side", "open", "days", "usdt", "days_red"])
    dd = eq / eq.cummax() - 1
    under = (eq < eq.cummax()).astype(int)
    longest_under = int(under.groupby((under == 0).cumsum()).sum().max())
    yr = eq.groupby(eq.index.year).last() / eq.groupby(eq.index.year).first().shift(1).fillna(EQ0).where(lambda x: x.index > eq.index.year.min(), EQ0) - 1
    yr = (1 + s).groupby(s.index.year).prod() - 1
    last12 = float((1 + s[s.index >= END - pd.Timedelta(days=366)]).prod() - 1)
    yrs = int(len(s) / 365)
    cagr = float((eq.iloc[-1] / EQ0) ** (365 / len(s)) - 1)
    sharpe = float(s.mean() / s.std() * np.sqrt(365)) if s.std() > 0 else 0.0
    ok = eq.iloc[-1] > EQ0 and dd.min() >= -0.20 and (yr > 0).sum() >= 4 and yr.get(2022, 0) >= -0.05 and last12 > 0
    wins, loss = Tr[Tr.usdt > 0], Tr[Tr.usdt <= 0]
    return {"end_equity": round(float(eq.iloc[-1]), 1), "cagr_pct": round(cagr * 100, 1), "sharpe": round(sharpe, 2),
            "max_dd_pct": round(float(dd.min()) * 100, 1), "longest_under_high_days": longest_under,
            "years_pct": {int(k): round(float(v) * 100, 1) for k, v in yr.items()}, "last12_pct": round(last12 * 100, 1),
            "avg_gross_exposure": round(float((np.abs(w).sum(axis=1))[m].mean()), 2),
            "positions": len(Tr), "pos_red_pct": round(float((Tr.usdt <= 0).mean() * 100), 1),
            "avg_hold_days": round(float(Tr.days.mean()), 1), "avg_win_usdt": round(float(wins.usdt.mean()), 2),
            "avg_loss_usdt": round(float(loss.usdt.mean()), 2), "median_days_red": float(Tr.days_red.median()),
            "max_days_red": int(Tr.days_red.max()), "verdict": "🟡 paper forward test" if ok else "🔴"}, eq, Tr


if __name__ == "__main__":
    C, Q = panel()
    out = {}
    P = "B" if DIV else "A"
    for name, short, coins in ((f"{P}1 long-only top20", False, None), (f"{P}2 long+short top20", True, None),
                               (f"{P}3 long-only BTC+ETH", False, ["BTCUSDT", "ETHUSDT"])):
        r, eq, Tr = run(C, Q, short, coins)
        out[name] = r
        eq.to_csv(HERE / f"equity_{name.split()[0]}.csv")
        Tr.to_csv(HERE / f"positions_{name.split()[0]}.csv", index=False)
        print(name, json.dumps(r), flush=True)
    (HERE / f"result_{P}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("DONE")
