"""CAP300 account simulator: what a real 300 USDT Binance USDT-M futures account can actually do.

Daily, sequential (equity path matters because minimum orders are absolute USDT amounts):
  * targets are fractions of current equity per coin (weights decided at the close of day t, held over t+1)
  * notional = weight x leverage x equity; a target below the coin's minimum notional is not opened
    (BTC 50, ETH 20, measured mainnet values; others default to 5 USDT)
  * an adjustment smaller than the coin's minimum is skipped (the position just drifts)
  * every executed USDT pays fee + slippage per side; funding is charged on the open notional
  * equity <= 0 ends the account (no recovery)
Trade P&L for PF/win-rate = contiguous holding of one coin (entry to exit), net of its costs.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FEE, SLIP = 0.0005, 0.0005


def min_notionals() -> dict[str, float]:
    d = json.loads((ROOT / "research" / "results" / "min_notional_mainnet.json").read_text(encoding="utf-8"))
    out = {}
    for r in d["rows"]:
        base = r["pair"].split("/")[0]
        out[base] = max(x for x in (r.get("cost_min"), r.get("notional_filter"), 5.0) if x is not None)
    return out


def simulate(W: pd.DataFrame, D: dict, equity0: float = 300.0, leverage: float = 1.0, cost_mult: float = 1.0,
             minn: dict | None = None, default_min: float = 5.0, trade_days: pd.Series | None = None) -> dict:
    """trade_days: optional boolean Series; orders are only placed on True days (positions drift otherwise),
    which is how a bot that only acts on its rebalance day behaves."""
    cols = list(W.columns)
    idx = W.index
    ret = D["ret"].reindex(index=idx, columns=cols).fillna(0.0).to_numpy()
    fund = D["funding"].reindex(index=idx, columns=cols).fillna(0.0).to_numpy()
    w = W.fillna(0.0).to_numpy()
    mins = np.array([(minn or {}).get(c, default_min) for c in cols])
    c_side = (FEE + SLIP) * cost_mult
    n = np.zeros(len(cols))                    # signed notional held
    trade_pnl = np.zeros(len(cols))            # running P&L of the open holding per coin
    trades, eq_path, n_pos, skipped, executed, cost_tot = [], [], [], 0, 0, 0.0
    equity = equity0
    td = None if trade_days is None else trade_days.reindex(idx).fillna(False).to_numpy(bool)
    for t in range(len(idx)):
        # P&L over day t on positions decided at the end of day t-1
        pnl = n * ret[t] - n * fund[t]
        equity += pnl.sum()
        trade_pnl += pnl
        n = n * (1 + ret[t])
        if equity <= 0:
            eq_path.append(0.0)
            n_pos.append(0)
            break
        if td is not None and not td[t]:
            eq_path.append(equity)
            n_pos.append(int((n != 0).sum()))
            continue
        # rebalance at the close of day t to the new targets
        tgt = w[t] * leverage * equity
        tgt = np.where(np.abs(tgt) < mins, 0.0, tgt)
        delta = tgt - n
        small = (np.abs(delta) < mins) & (tgt != 0) & (n != 0)
        skipped += int((((np.abs(w[t] * leverage * equity) < mins) & (w[t] != 0))).sum()) + int(small.sum())
        delta = np.where(small, 0.0, delta)
        # a holding ends when the position goes flat OR flips direction
        closing = (n != 0) & (delta != 0) & ((tgt == 0) | (np.sign(tgt) != np.sign(n)))
        cost = np.abs(delta) * c_side
        equity -= cost.sum()
        cost_tot += cost.sum()
        trade_pnl -= cost
        executed += int((delta != 0).sum())
        for j in np.flatnonzero(closing):
            trades.append(trade_pnl[j])
            trade_pnl[j] = 0.0
        n = n + delta
        eq_path.append(equity)
        n_pos.append(int((n != 0).sum()))
    for j in np.flatnonzero(n != 0):
        trades.append(trade_pnl[j])
    eq = pd.Series(eq_path, index=idx[:len(eq_path)])
    return {"equity": eq, "trades": np.array(trades), "positions": pd.Series(n_pos, index=eq.index),
            "skipped": skipped, "executed": executed, "costs": cost_tot}


REGIMES = {"2021": ("2021-01-01", "2021-12-31"), "2022": ("2022-01-01", "2022-12-31"),
           "2023_24": ("2023-01-01", "2024-12-31"), "2025_26": ("2025-01-01", "2026-12-31")}
FOLDS = [(f"{y}H{h}", f"{y}-{'01' if h == 1 else '07'}-01", f"{y + (h == 2)}-{'07' if h == 1 else '01'}-01")
         for y, h in [(2022, 2), (2023, 1), (2023, 2), (2024, 1), (2024, 2), (2025, 1), (2025, 2), (2026, 1)]]


def metrics(r: dict, equity0: float = 300.0) -> dict:
    eq, tr = r["equity"], r["trades"]
    eq = eq[eq.index >= eq.index[0]]
    start = eq.ne(equity0).idxmax() if eq.ne(equity0).any() else eq.index[0]
    e = eq.loc[start:]
    dr = e.pct_change().fillna(0.0)
    yrs = max(len(e) / 365.25, 1e-9)
    gw, gl = tr[tr > 0].sum(), -tr[tr < 0].sum()
    out = {"final": round(float(e.iloc[-1]), 2), "total": float(e.iloc[-1] / equity0 - 1),
           "cagr": float((e.iloc[-1] / equity0) ** (1 / yrs) - 1) if e.iloc[-1] > 0 else -1.0,
           "max_dd": float(-(e / e.cummax() - 1).min()), "sharpe": float(dr.mean() / dr.std() * np.sqrt(365)) if dr.std() > 0 else 0.0,
           "pf": float(gw / gl) if gl > 0 else None, "trades": int(len(tr)), "win": float((tr > 0).mean()) if len(tr) else None,
           "avg_positions": float(r["positions"][r["positions"] > 0].mean()) if (r["positions"] > 0).any() else 0.0,
           "invested_days": float((r["positions"] > 0).mean()), "skipped_orders": r["skipped"], "executed_orders": r["executed"],
           "costs_usdt": round(float(r["costs"]), 2)}
    for k, (a, b) in REGIMES.items():
        s = e.loc[a:b]
        out["reg_" + k] = float(s.iloc[-1] / s.iloc[0] - 1) if len(s) > 1 else 0.0
    folds = {}
    for n_, a, b in FOLDS:
        s = e.loc[a:b]
        folds[n_] = float(s.iloc[-1] / s.iloc[0] - 1) if len(s) > 1 else 0.0
    out["folds"] = folds
    out["daily"] = dr
    return out
