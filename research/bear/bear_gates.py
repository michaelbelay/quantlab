"""Step 1 gates of RULES_BEAR incl. Amendment A2 robustness gates, and step 2 (300 USDT, 6 slots of 50 USDT)."""
from __future__ import annotations

import numpy as np
import pandas as pd

MID = pd.Timestamp("2024-05-01", tz="UTC")


def stats(tr: pd.DataFrame) -> dict:
    """tr: entry, net, net2x[, short_leg]. Returns numbers, verdict and the failed gates."""
    if tr.empty:
        return {"trades": 0, "verdict": "🔴", "fails": "no trades"}
    a, b = tr[tr.entry < MID], tr[tr.entry >= MID]
    m = tr.groupby(tr.entry.dt.strftime("%Y-%m")).net.sum()
    yr = tr.groupby(tr.entry.dt.year).net.mean()
    tot = tr.net.sum()
    top3 = 100 * m.nlargest(3).sum() / tot if tot > 0 else np.nan
    wo10 = tr.net.sort_values().iloc[:-10].mean() if len(tr) > 10 else np.nan
    s = {"trades": len(tr), "A": len(a), "B": len(b), "win": round(100 * (tr.net > 0).mean(), 1),
         "avg": round(100 * tr.net.mean(), 3), "avg_A": round(100 * a.net.mean(), 3) if len(a) else None,
         "avg_B": round(100 * b.net.mean(), 3) if len(b) else None, "avg_2x": round(100 * tr.net2x.mean(), 3),
         "months_pos": f"{int((m > 0).sum())}/{len(m)}", "top3_months_pct": round(top3, 1) if top3 == top3 else None,
         "avg_wo_top10": round(100 * wo10, 3) if wo10 == wo10 else None,
         "years": {str(y): [int((tr.entry.dt.year == y).sum()), round(100 * v, 2)] for y, v in yr.items()},
         "worst": [(r.coin, str(r.entry)[:10], round(100 * r.net, 2)) for r in tr.nsmallest(3, "net").itertuples()],
         "best": [(r.coin, str(r.entry)[:10], round(100 * r.net, 2)) for r in tr.nlargest(3, "net").itertuples()]}
    if "short_leg" in tr:
        s["short_leg"] = round(100 * tr.short_leg.mean(), 3)
    f = []
    if len(tr) < 150 or len(a) < 50 or len(b) < 50:
        f.append("trade count")
    if not (len(a) and len(b) and a.net.mean() >= 0.003 and b.net.mean() >= 0.003):
        f.append("avg < +0.30% in a half")
    if tr.net2x.mean() <= 0:
        f.append("loses at 2x costs")
    if (m > 0).mean() < 0.55:
        f.append("months < 55%")
    if not (top3 == top3 and top3 <= 50):
        f.append("top 3 months > 50%")
    if not (wo10 == wo10 and wo10 > 0):
        f.append("<= 0 without 10 best")
    if (yr > 0).sum() < 3:
        f.append("< 3 positive years")
    if "short_leg" in tr and tr.short_leg.mean() <= 0:
        f.append("short side loses")
    s["verdict"], s["fails"] = ("🔴" if f else "🟠"), ", ".join(f)
    return s


def step2(paths: list[tuple[int, np.ndarray]], n_hours: int, index, cost_per_trade: float, mult: int,
          leg_usdt: float = 50.0, slots: int = 6, legs_per_trade: int = 1) -> dict:
    """300 USDT account, hourly marked to market. paths: (entry bar, gross+funding path per bar from entry).
    Trades are taken in entry order while a slot is free; a pair uses 2 slots and leg_usdt per leg."""
    pnl = np.zeros(n_hours)
    busy_until: list[int] = []
    taken, worst = 0, 0.0
    for i, p in sorted(paths, key=lambda x: x[0]):
        busy_until = [j for j in busy_until if j >= i]
        if len(busy_until) + legs_per_trade > slots:
            continue
        j = i + len(p) - 1
        busy_until += [j] * legs_per_trade
        v = leg_usdt * (p - cost_per_trade * mult)
        pnl[i:j + 1] += v
        pnl[j + 1:] += v[-1]
        worst = min(worst, float(v[-1]))
        taken += 1
    eq = pd.Series(300 + pnl, index=index)
    dd = float(100 * (eq / eq.cummax() - 1).min())
    return {"taken": taken, "profit_usdt": round(float(eq.iloc[-1] - 300), 1), "max_dd_pct": round(dd, 1),
            "worst_trade_usdt": round(worst, 1),
            "by_year_usdt": {str(y): round(float(g.iloc[-1] - g.iloc[0]), 1) for y, g in eq.groupby(eq.index.year)}}
