"""How does FlowTrend (the paper trader's strategy, its own signal code, its 20 coins) do on bear days? Description only.

    .venv\\Scripts\\python.exe research\\bear\\flowtrend_bear_split.py

Every signal 2022-01 .. 2026-09 simulated on its own (no slot limit): entry at the next open, FlowTrend's stop, 48h exit,
0.20% round trip + real funding. Split by side x bear day (RULES_BEAR: BTC 20-day return <= 0). Output batch4/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from trader import flowtrend as ft  # noqa: E402
from trader.replay import load  # noqa: E402
from trader.settings import COINS, FUTURES  # noqa: E402

OUT = Path(__file__).resolve().parent / "batch4"
START, MID, END = pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2024-05-01", tz="UTC"), pd.Timestamp("2026-10-01", tz="UTC")
COST = 0.002


def bear_days() -> pd.Series:
    b = pd.read_feather(FUTURES / "BTC_USDT_USDT-1h-futures.feather").drop_duplicates("date").set_index("date").close
    d = b[b.index.hour == 23]
    d.index = d.index.normalize() + pd.Timedelta(days=1)
    return d / d.shift(20) - 1 <= 0


def funding(c: str) -> pd.Series:
    f = FUTURES / f"{c}_USDT_USDT-1h-funding_rate.feather"
    return pd.read_feather(f).drop_duplicates("date").set_index("date").funding_rate if f.exists() else pd.Series(dtype=float)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bear = bear_days()
    frames = {c: ft.indicators(load(c)) for c in COINS}
    S = ft.signals(frames)
    S = S[(S.time + pd.Timedelta(hours=1) >= START) & (S.time + pd.Timedelta(hours=1) < END)]
    rows = []
    for s in S.itertuples(index=False):
        t_in = s.time + pd.Timedelta(hours=1)
        fut = frames[s.coin].loc[t_in: t_in + pd.Timedelta(hours=ft.HOLD_H - 1)]
        if len(fut) < ft.HOLD_H:
            continue
        e = float(fut.open.iat[0])
        stop = ft.stop_price(e, s.sig24, s.short)
        hit = (fut.high >= stop) if s.short else (fut.low <= stop)
        j = int(hit.values.argmax()) if hit.any() else ft.HOLD_H - 1
        px = stop if hit.any() else float(fut.close.iat[-1])
        t_out = fut.index[j] + pd.Timedelta(hours=1)
        side = -1 if s.short else 1
        f = funding(s.coin)
        fund = -side * float(f[(f.index > t_in) & (f.index <= t_out)].sum())
        gross = side * (px / e - 1)
        rows.append({"coin": s.coin, "entry": t_in, "side": "short" if s.short else "long",
                     "bear": bool(bear.get(t_in.normalize(), False)), "why": "stop" if hit.any() else "time",
                     "gross": gross, "funding": fund, "net": gross + fund - COST})
    T = pd.DataFrame(rows).sort_values("net")
    T.to_csv(OUT / "flowtrend_trades.csv", index=False)
    res = {}
    for (side, br), g in T.groupby(["side", "bear"]):
        a, b = g[g.entry < MID], g[g.entry >= MID]
        res[f"{side} {'bear' if br else 'not bear'}"] = {
            "trades": len(g), "avg_net": round(100 * g.net.mean(), 3), "win_pct": round(100 * (g.net > 0).mean(), 1),
            "avg_A": round(100 * a.net.mean(), 3) if len(a) else None, "avg_B": round(100 * b.net.mean(), 3) if len(b) else None,
            "trades_A": len(a), "trades_B": len(b),
            "years": {str(y): [len(x), round(100 * x.net.mean(), 3)] for y, x in g.groupby(g.entry.dt.year)},
            "worst": [(r.coin, str(r.entry)[:10], round(100 * r.net, 2)) for r in g.head(3).itertuples()]}
    (OUT / "flowtrend_split.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, v in res.items():
        print(k, json.dumps(v))


if __name__ == "__main__":
    main()
