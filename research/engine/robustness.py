"""Anti-overfitting checks and portfolio construction.

Three independent ways a candidate can be exposed as fragile:

 * PARAMETER NEIGHBOURS -- re-run with stop/TP/lookback nudged +-25%. A real
   edge degrades gracefully; a curve-fit collapses. The degradation becomes the
   `instability` penalty term in the composite score.
 * COST SENSITIVITY -- re-run with fees and slippage doubled. Every strategy
   killed earlier in this project died here.
 * COIN HOLDOUT -- re-run on eight coins that played no part in any decision.
"""
from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from backtest import FEE, SLIP, simulate
import backtest as bt
from generate import to_config
from tournament import EQUITY, composite, metrics, period_consistency


def _score_of(trades, universe):
    m = metrics(trades)
    cons, _ = period_consistency(trades, universe)
    return composite(m, cons), m


def neighbours(cand: dict) -> list[dict]:
    """Nudged variants of one candidate."""
    out = []
    for mult in (0.75, 1.25):
        c = copy.deepcopy(cand)
        c["cfg"]["stop_atr"] = round(c["cfg"].get("stop_atr", 2.0) * mult, 3)
        c["id"] += f"|stop{mult}"
        out.append(c)
    for mult in (0.8, 1.2):
        c = copy.deepcopy(cand)
        tps = c["cfg"].get("tp_atr", ())
        if tps:
            c["cfg"]["tp_atr"] = tuple(round(t * mult, 3) if t < 50 else t for t in tps)
            c["id"] += f"|tp{mult}"
            out.append(c)
    for lb in (14, 30):
        c = copy.deepcopy(cand)
        c["spec"] = copy.deepcopy(c["spec"])
        c["spec"].setdefault("params", {})["lookback"] = lb
        c["id"] += f"|lb{lb}"
        out.append(c)
    return out


def parameter_stability(cand: dict, universe, base_score: float, leverage=2.0) -> dict:
    """Fraction of neighbours that stay profitable, and mean score drop."""
    scores, rets = [], []
    for nb in neighbours(cand):
        tr = simulate(universe, nb["spec"], to_config(nb["cfg"], leverage))
        sc, m = _score_of(tr, universe)
        scores.append(-1.0 if sc.disqualified else sc.total)
        rets.append(m["ret_pct"])
    if not scores:
        return {"instability": 1.0, "neighbours_profitable": 0, "n": 0}
    good = sum(1 for r in rets if r > 0)
    mean_s = float(np.mean(scores))
    drop = max(0.0, (base_score - mean_s) / (abs(base_score) + 1e-9))
    return {"instability": round(min(drop, 1.5), 3),
            "neighbours_profitable": good, "n": len(scores),
            "neighbour_returns": [round(r, 1) for r in rets],
            "mean_neighbour_score": round(mean_s, 3)}


def cost_sensitivity(cand: dict, universe, leverage=2.0, mult=2.0) -> dict:
    """Double fees and slippage; a thin edge dies here."""
    old_fee, old_slip = bt.FEE, bt.SLIP
    bt.FEE, bt.SLIP = old_fee * mult, old_slip * mult
    try:
        tr = simulate(universe, cand["spec"], to_config(cand["cfg"], leverage))
        m = metrics(tr)
    finally:
        bt.FEE, bt.SLIP = old_fee, old_slip
    return {"ret_pct_2x_costs": m["ret_pct"], "pf_2x_costs": m["pf"],
            "trades_2x_costs": m["trades"]}


def monthly_returns(trades, dates) -> pd.Series:
    if not trades:
        return pd.Series(dtype=float)
    rows = {}
    for t in trades:
        d = pd.Timestamp(dates[min(t.exit_i, len(dates) - 1)])
        if d.tzinfo is not None:
            d = d.tz_localize(None)
        k = f"{d.year}-{d.month:02d}"
        rows[k] = rows.get(k, 0.0) + t.pnl
    return pd.Series(rows).sort_index() / EQUITY * 100


def build_portfolio(finalists: list[tuple[str, list]], dates, max_n=5,
                    max_corr=0.6) -> list[str]:
    """Greedy low-correlation selection -- avoid five copies of one strategy."""
    series = {sid: monthly_returns(tr, dates) for sid, tr in finalists}
    idx = sorted(set().union(*[set(s.index) for s in series.values()])) if series else []
    mat = pd.DataFrame({k: v.reindex(idx).fillna(0) for k, v in series.items()})
    chosen: list[str] = []
    for sid, _ in finalists:                     # finalists arrive pre-ranked
        if len(chosen) >= max_n:
            break
        if not chosen:
            chosen.append(sid)
            continue
        c = max(abs(mat[sid].corr(mat[o])) for o in chosen)
        if not np.isnan(c) and c <= max_corr:
            chosen.append(sid)
    return chosen, mat
