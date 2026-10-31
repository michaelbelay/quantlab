"""Protocol C portfolio replay on a 300 USDT account + the spec's metric set.

Trades from all coins are replayed in time order. A trade is taken only if a slot is free, the same-direction
cap allows it (and, for the balanced book, |longs - shorts| stays <= 2), and stake x leverage meets the coin's
minimum order. Stake = equity / slots (realised equity at the entry time). P&L is realised at exit.
"""
from __future__ import annotations

import heapq

import numpy as np
import pandas as pd

START = 300.0


def replay(trades: pd.DataFrame, min_notional: dict, slots: int = 20, max_same: int = 10, lev: float = 1.0,
           balanced: bool = False, mmr: float = 0.01) -> tuple[pd.DataFrame, pd.Series]:
    t = trades.sort_values("entry_t").reset_index(drop=True)
    eq = START
    open_heap: list = []                 # (exit_t, idx)
    n_long = n_short = 0
    taken = np.zeros(len(t), bool)
    pnl = np.zeros(len(t))
    stake_arr = np.zeros(len(t))
    curve_t, curve_v = [t["entry_t"].iloc[0] if len(t) else pd.Timestamp("2021-01-01", tz="UTC")], [START]
    liq = np.zeros(len(t), bool)
    for i, row in enumerate(t.itertuples(index=False)):
        while open_heap and open_heap[0][0] <= row.entry_t:
            xt, j = heapq.heappop(open_heap)
            eq += pnl[j]
            curve_t.append(xt)
            curve_v.append(eq)
            if t.at[j, "side"] == 1:
                n_long -= 1
            else:
                n_short -= 1
        if eq <= 0:
            break
        if n_long + n_short >= slots:
            continue
        if row.side == 1 and (n_long >= max_same or (balanced and n_long - n_short >= 2)):
            continue
        if row.side == -1 and (n_short >= max_same or (balanced and n_short - n_long >= 2)):
            continue
        stake = eq / slots
        if stake * lev < min_notional.get(row.coin, 5.0):
            continue
        r = row.ret
        if lev > 1 and row.mae <= -(1 / lev - mmr):          # liquidated before the planned exit
            r, liq[i] = -1.0 / lev, True
        pnl[i] = stake * lev * r
        stake_arr[i] = stake
        taken[i] = True
        heapq.heappush(open_heap, (row.exit_t, i))
        if row.side == 1:
            n_long += 1
        else:
            n_short += 1
    while open_heap:
        xt, j = heapq.heappop(open_heap)
        eq += pnl[j]
        curve_t.append(xt)
        curve_v.append(eq)
    t["taken"], t["pnl"], t["stake"], t["liquidated"] = taken, pnl, stake_arr, liq
    curve = pd.Series(curve_v, index=pd.to_datetime(curve_t, utc=True)).sort_index()
    return t, curve


def metrics(t: pd.DataFrame, curve: pd.Series, periods: list[tuple[str, str, str]]) -> dict:
    tk = t[t["taken"]]
    if len(tk) == 0:
        return {"trades": 0}
    daily = curve.resample("1D").last().ffill()
    dr = daily.pct_change().dropna()
    yrs = max((curve.index[-1] - curve.index[0]).days / 365.25, 1e-9)
    final = float(curve.iloc[-1])
    dd = float((1 - curve / curve.cummax()).max())
    wins, losses = tk.loc[tk["pnl"] > 0, "pnl"].sum(), -tk.loc[tk["pnl"] < 0, "pnl"].sum()
    neg = dr[dr < 0]
    monthly = daily.resample("ME").last().pct_change().dropna()
    yearly = daily.resample("YE").last().pct_change().dropna()
    streak = mx = 0
    for v in tk["pnl"]:
        streak = streak + 1 if v < 0 else 0
        mx = max(mx, streak)
    per = {}
    for name, a, b in periods:
        w = tk[(tk["exit_t"] >= pd.Timestamp(a, tz="UTC")) & (tk["exit_t"] < pd.Timestamp(b, tz="UTC"))]
        per[name] = round(float(w["pnl"].sum()), 2)
    by_coin = tk.groupby("coin")["pnl"].sum()
    held = (tk["exit_t"] - tk["entry_t"]).dt.total_seconds().sum() / 86400
    side = {s: {"trades": int((tk["side"] == v).sum()), "pnl": round(float(tk.loc[tk["side"] == v, "pnl"].sum()), 2),
                "pf": round(float(tk.loc[(tk["side"] == v) & (tk["pnl"] > 0), "pnl"].sum()
                                  / max(1e-9, -tk.loc[(tk["side"] == v) & (tk["pnl"] < 0), "pnl"].sum())), 3)}
            for s, v in (("long", 1), ("short", -1))}
    return {
        "final": round(final, 2), "net": round(final - START, 2),
        "cagr_pct": round(((final / START) ** (1 / yrs) - 1) * 100, 1) if final > 0 else -100.0,
        "max_dd_pct": round(dd * 100, 1), "pf": round(float(wins / max(losses, 1e-9)), 3),
        "sharpe": round(float(dr.mean() / dr.std() * np.sqrt(365)), 2) if dr.std() > 0 else 0.0,
        "sortino": round(float(dr.mean() / neg.std() * np.sqrt(365)), 2) if len(neg) > 1 and neg.std() > 0 else 0.0,
        "win_rate": round(float((tk["pnl"] > 0).mean() * 100), 1),
        "avg_trade_pct": round(float(tk["ret"].mean() * 100), 3), "median_trade_pct": round(float(tk["ret"].median() * 100), 3),
        "trades": int(len(tk)), "signals": int(len(t)), "trades_per_year": round(len(tk) / yrs, 1),
        "long": side["long"], "short": side["short"],
        "worst_month_pct": round(float(monthly.min() * 100), 1) if len(monthly) else None,
        "worst_year_pct": round(float(yearly.min() * 100), 1) if len(yearly) else None,
        "max_consecutive_losses": int(mx), "exposure_pct": round(float(held / (yrs * 365.25) / 20 * 100), 1),
        "return_over_dd": round(float((final / START - 1) / max(dd, 1e-9)), 2),
        "periods": per, "periods_positive": sum(v > 0 for v in per.values()),
        "top_coin_share": round(float(by_coin.max() / by_coin[by_coin > 0].sum()), 3) if (by_coin > 0).any() else None,
        "liquidations": int(tk["liquidated"].sum()), "exits": tk["reason"].value_counts().to_dict(),
    }
