"""Replay FlowTrend over the saved 1h history with the trader's own signal code, to check it matches the research.

    .venv\\Scripts\\python.exe -m trader.replay
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import flowtrend as ft
from .settings import COINS, FUTURES, MARKET, SLOTS, min_cost

FEE = 0.0005
START, END = pd.Timestamp("2024-04-01", tz="UTC"), pd.Timestamp("2026-10-01", tz="UTC")


def load(c: str) -> pd.DataFrame:
    d = pd.read_feather(FUTURES / f"{c}_USDT_USDT-1h-futures.feather").drop_duplicates("date").set_index("date").sort_index()
    q = pd.read_feather(MARKET / "flow" / f"{c}.feather").drop_duplicates("date")
    q = q.set_index(pd.to_datetime(q["date"], utc=True))[["quote_volume", "taker_buy_quote"]]
    d = d.join(q.rename(columns={"quote_volume": "qv", "taker_buy_quote": "tbq"}), how="left")
    return d[d.index < END]


def main(wallet: float = 300.0) -> dict:
    frames = {c: ft.indicators(load(c)) for c in COINS}
    S = ft.signals(frames)
    S = S[(S.time + pd.Timedelta(hours=1) >= START) & (S.time + pd.Timedelta(hours=1) < END)]
    bal, opened, trades = wallet, [], []
    for s in S.itertuples(index=False):
        t_in = s.time + pd.Timedelta(hours=1)
        for o in [o for o in opened if o["exit_t"] <= t_in]:
            bal += o["usdt"]; opened.remove(o)
        if len(opened) >= SLOTS or any(o["coin"] == s.coin for o in opened):
            continue
        d = frames[s.coin]
        fut = d.loc[t_in: t_in + pd.Timedelta(hours=ft.HOLD_H - 1)]
        if len(fut) < ft.HOLD_H:
            continue
        e = float(fut.open.iat[0])
        stop = ft.stop_price(e, s.sig24, s.short)
        hit = (fut.high >= stop) if s.short else (fut.low <= stop)
        if hit.any():
            j = int(np.argmax(hit.values)); px, why = stop, "stop"
        else:
            j = ft.HOLD_H - 1; px, why = float(fut.close.iat[-1]), "time_48h"
        r = (1 - px / e) if s.short else (px / e - 1)       # futures: profit is linear in price for both sides
        stake = (bal - sum(o["stake"] for o in opened)) / (SLOTS - len(opened))
        if stake < min_cost(s.coin):                  # below Binance's minimum order -> the order is refused
            continue
        o = {"coin": s.coin, "short": s.short, "open": t_in, "exit_t": fut.index[j] + pd.Timedelta(hours=1),
             "stake": stake, "usdt": stake * (r - 2 * FEE), "why": why}
        opened.append(o); trades.append(o)
    for o in opened:
        bal += o["usdt"]
    T = pd.DataFrame(trades)
    ref = pd.read_csv(MARKET / "ref_flowtrend_trades.csv", parse_dates=["open_date"])
    ref_keys = set(zip(ref.pair.str.split("/").str[0], ref.open_date, ref.is_short))
    sig_keys = set(zip(S.coin, S.time + pd.Timedelta(hours=1), S.short))
    mine = set(zip(T.coin, T.open, T.short))
    out = {"signals": len(S), "trades": len(T), "final": round(bal, 2),
           "reference_trades": len(ref), "reference_entries_found_in_signals": len(ref_keys & sig_keys),
           "same_trades_as_reference": len(ref_keys & mine)}
    print(json.dumps(out))
    return out


if __name__ == "__main__":
    main()
