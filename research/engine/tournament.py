"""Metrics, composite scoring and the anti-degenerate-solution machinery.

The central failure this file exists to prevent: an optimiser discovering that
the safest way to score well is to stop trading. Three mechanisms block that.

 1. HARD FLOOR -- below `min_trades` a candidate is disqualified outright and
    can never rank, regardless of how pretty its other numbers look.
 2. STATISTICAL RELIABILITY -- the headline term is the t-statistic of mean R,
    mean_R / (sd_R / sqrt(n)). A 2-trade 100%-win strategy has a large mean but
    tiny n, so its t-stat is small. Evidence has to be earned.
 3. ACTIVITY TERM -- a strategy is rewarded for trading enough to be usable,
    saturating so that churn is not rewarded either.

Nothing here ranks on a single metric, and `explain()` prints every term.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

EQUITY = 1000.0
# Trade-frequency floors. The first version of this file used 80 trades over
# 5.7 years -- 14 a year -- which let strategies that barely trade rank as
# winners. That is the degenerate solution this module exists to prevent, so the
# floor is now expressed as a usable frequency across the 8-pair portfolio.
SPAN_YEARS = 5.7
MIN_TRADES_PER_YEAR = 100        # ~2 per week across the portfolio
MIN_TRADES = int(MIN_TRADES_PER_YEAR * SPAN_YEARS)      # 570
GOOD_TRADES = int(300 * SPAN_YEARS)                     # activity saturates ~5/wk
MIN_PF = 1.15            # margin of safety above modelled costs
MIN_EXPECTANCY_R = 0.05  # per-trade edge in units of risk
MIN_EXPECTANCY_PCT = 0.15  # net edge per trade as % of notional (costs ~0.2%)


def equity_curve(trades: list) -> pd.Series:
    if not trades:
        return pd.Series(dtype=float)
    s = sorted(trades, key=lambda t: t.exit_i)
    return pd.Series(np.cumsum([t.pnl for t in s]))


def max_dd(trades: list) -> float:
    eq = EQUITY + equity_curve(trades)
    if eq.empty:
        return 0.0
    peak = eq.cummax()
    return float(((peak - eq) / peak).max() * 100)


def metrics(trades: list, dates=None) -> dict:
    n = len(trades)
    if n == 0:
        return {"trades": 0, "ret_pct": 0.0, "pf": 0.0, "expectancy_r": 0.0,
                "win_rate": 0.0, "t_stat": 0.0, "max_dd": 0.0, "disqualified": True,
                "reason": "zero trades"}
    pnl = np.array([t.pnl for t in trades], dtype=float)
    r = np.array([t.r for t in trades], dtype=float)
    wins, losses = pnl[pnl > 0], pnl[pnl < 0]
    gross_w, gross_l = wins.sum(), abs(losses.sum())
    sd = r.std(ddof=1) if n > 1 else 0.0
    t_stat = (r.mean() / (sd / math.sqrt(n))) if sd > 0 else 0.0

    longs = [t for t in trades if t.side > 0]
    shorts = [t for t in trades if t.side < 0]
    m = {
        "trades": n,
        "ret_pct": round(pnl.sum() / EQUITY * 100, 2),
        "win_rate": round(len(wins) / n * 100, 1),
        "pf": round(gross_w / gross_l, 3) if gross_l > 0 else (99.0 if gross_w > 0 else 0.0),
        "expectancy_r": round(float(r.mean()), 4),
        "expectancy_usd": round(float(pnl.mean()), 2),
        # edge per trade as a % of notional -- comparable across stop styles,
        # and directly measurable against the ~0.2% round-trip cost
        "expectancy_pct": round(float(np.mean([t.pnl / t.notional * 100
                                               for t in trades if t.notional])), 4),
        "t_stat": round(float(t_stat), 2),
        "max_dd": round(max_dd(trades), 2),
        "avg_win": round(float(wins.mean()), 2) if len(wins) else 0.0,
        "avg_loss": round(float(losses.mean()), 2) if len(losses) else 0.0,
        "avg_bars": round(float(np.mean([t.bars for t in trades])), 1),
        "long_trades": len(longs), "short_trades": len(shorts),
        "long_pct": round(sum(t.pnl for t in longs) / EQUITY * 100, 2),
        "short_pct": round(sum(t.pnl for t in shorts) / EQUITY * 100, 2),
        "tp1": round(sum(1 for t in trades if t.tp_hits >= 1) / n * 100, 1),
        "tp2": round(sum(1 for t in trades if t.tp_hits >= 2) / n * 100, 1),
        "tp3": round(sum(1 for t in trades if t.tp_hits >= 3) / n * 100, 1),
        "tp4": round(sum(1 for t in trades if t.tp_hits >= 4) / n * 100, 1),
        "liquidations": sum(1 for t in trades if t.reason == "liquidation"),
        "max_consec_loss": _max_consec(pnl),
        "trades_per_year": round(n / SPAN_YEARS, 1),
        "trades_per_month": round(n / (SPAN_YEARS * 12), 2),
        "disqualified": n < MIN_TRADES,
        "reason": "" if n >= MIN_TRADES else
                  f"trades too rarely: {n} ({round(n/SPAN_YEARS)}/yr < {MIN_TRADES_PER_YEAR}/yr)",
    }
    sharpe = (r.mean() / sd * math.sqrt(252 * 24 / max(m["avg_bars"], 1))) if sd > 0 else 0.0
    downside = r[r < 0].std(ddof=1) if (r < 0).sum() > 1 else 0.0
    m["sharpe"] = round(float(sharpe), 2)
    m["sortino"] = round(float(r.mean() / downside * math.sqrt(252)), 2) if downside > 0 else 0.0
    return m


def _max_consec(pnl: np.ndarray) -> int:
    worst = cur = 0
    for x in pnl:
        cur = cur + 1 if x < 0 else 0
        worst = max(worst, cur)
    return worst


def regime_breakdown(trades: list) -> dict:
    """P&L split by the regime in force when the trade was opened."""
    out = {}
    for t in trades:
        d = out.setdefault(t.regime, {"n": 0, "pnl": 0.0})
        d["n"] += 1
        d["pnl"] += t.pnl
    return {k: {"n": v["n"], "pct": round(v["pnl"] / EQUITY * 100, 2)}
            for k, v in sorted(out.items())}


def period_consistency(trades: list, feats) -> tuple[float, dict]:
    """Fraction of calendar half-years that were profitable."""
    if not trades:
        return 0.0, {}
    any_f = next(iter(feats.values()))
    dates = any_f.date
    buckets: dict[str, float] = {}
    for t in trades:
        d = pd.Timestamp(dates[min(t.exit_i, len(dates) - 1)])
        key = f"{d.year}H{1 if d.month <= 6 else 2}"
        buckets[key] = buckets.get(key, 0.0) + t.pnl
    pos = sum(1 for v in buckets.values() if v > 0)
    return (pos / len(buckets) if buckets else 0.0), \
        {k: round(v / EQUITY * 100, 2) for k, v in sorted(buckets.items())}


@dataclass
class Score:
    total: float
    terms: dict
    disqualified: bool
    reason: str

    def explain(self) -> str:
        if self.disqualified:
            return f"DISQUALIFIED: {self.reason}"
        parts = "  ".join(f"{k}={v:+.3f}" for k, v in self.terms.items())
        return f"score={self.total:.3f}  [{parts}]"


WEIGHTS = {
    "reliability": 0.30,   # t-stat of mean R -- sample-size aware
    "profit_factor": 0.20,
    "expectancy": 0.15,
    "consistency": 0.15,
    "activity": 0.10,
    "drawdown": -0.25,
    "instability": -0.20,  # filled in by robustness testing
    "exposure": -0.05,
}


def composite(m: dict, consistency: float, instability: float = 0.0,
              exposure: float = 0.0) -> Score:
    """Transparent weighted score. Never let one metric decide."""
    if m.get("disqualified"):
        return Score(-999.0, {}, True, m.get("reason", "disqualified"))
    if m["ret_pct"] <= 0:
        return Score(-999.0, {}, True, f"unprofitable ({m['ret_pct']}%)")

    # Margin-of-safety floors. The first walk-forward run selected strategies
    # with PF ~1.07 over thousands of trades; that edge is thinner than the
    # uncertainty in our own cost assumptions, and it duly died out-of-sample.
    # A candidate must clear costs by a visible margin to be rankable.
    if m["pf"] < MIN_PF:
        return Score(-999.0, {}, True, f"profit factor {m['pf']} < {MIN_PF}")
    if m["expectancy_pct"] < MIN_EXPECTANCY_PCT:
        return Score(-999.0, {}, True,
                     f"edge {m['expectancy_pct']}%/trade < {MIN_EXPECTANCY_PCT}%")

    # Implausibility guard. Results this clean do not occur in real markets;
    # in practice they mean lookahead or a data-leak bug, so refuse to rank
    # them rather than celebrate them. (This caught a genuine bug in the
    # resampled volatility family during development.)
    if m["win_rate"] > 90 or m["pf"] > 10 or (m["max_dd"] < 2.0 and m["trades"] > 100):
        return Score(-999.0, {}, True,
                     f"IMPLAUSIBLE (win {m['win_rate']}%, pf {m['pf']}, "
                     f"dd {m['max_dd']}%) - suspect lookahead/leak")

    n = m["trades"]
    terms = {
        "reliability": math.tanh(m["t_stat"] / 3.0),
        "profit_factor": min((m["pf"] - 1.0) / 1.0, 1.0) if m["pf"] > 0 else -1,
        "expectancy": math.tanh(m["expectancy_pct"] / 1.5),
        "consistency": 2 * consistency - 1,
        "activity": min(n / GOOD_TRADES, 1.0),
        "drawdown": min(m["max_dd"] / 35.0, 2.0),
        "instability": instability,
        "exposure": exposure,
    }
    total = sum(WEIGHTS[k] * v for k, v in terms.items())
    # liquidations are disqualifying -- they mean the sizing was wrong
    if m.get("liquidations", 0) > 0:
        return Score(-999.0, terms, True, f"{m['liquidations']} liquidations")
    return Score(round(total, 4), {k: round(v, 3) for k, v in terms.items()}, False, "")
