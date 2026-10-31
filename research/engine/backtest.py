"""Event-driven backtester with staged entries, a TP ladder and realistic costs.

Deliberately pessimistic where the bar data is ambiguous:
  * if a bar's range covers both the stop and a take-profit, the STOP is taken
    first -- intrabar order is unknowable, so we assume the worse one;
  * entries and exits both pay fee + slippage;
  * futures funding is charged every bar a position is held;
  * a position that moves against us past the liquidation distance implied by
    leverage is closed there, not at some later friendly price.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from features import PairFeatures
from signals import build_signals

FEE = 0.0005          # per side, taker
SLIP = 0.0005         # per side


@dataclass
class Trade:
    pair: str
    side: int                 # +1 long, -1 short
    entry_i: int
    exit_i: int = -1
    entry: float = 0.0
    exit: float = 0.0
    size: float = 1.0
    pnl: float = 0.0          # in equity currency, after costs
    r: float = 0.0            # result in units of initial risk
    reason: str = ""
    tp_hits: int = 0
    score: float = 0.0
    bars: int = 0
    regime: str = ""
    funding_paid: float = 0.0
    notional: float = 0.0


@dataclass
class Config:
    stake_pct: float = 0.10       # notional fraction of equity per trade
    leverage: float = 2.0
    stop_mode: str = "atr"        # atr | structure
    stop_atr: float = 2.0
    tp_mode: str = "atr"          # atr | structure | none
    tp_atr: tuple = (1.5, 3.0, 5.0, 8.0)
    tp_frac: tuple = (0.50, 0.25, 0.15, 0.10)
    breakeven_after_tp1: bool = True
    trail_after_tp: int = 0       # 0 = off; else trail once N tps hit
    trail_atr: float = 2.5
    entry_mode: str = "instant"   # instant | split
    split_frac: tuple = (0.5, 0.25, 0.25)
    split_pullback_atr: float = 0.7
    split_window: int = 8
    osc_exit: bool = False        # close remainder on opposing oscillator after TP1
    max_bars: int = 400
    cooldown: int = 3
    max_concurrent: int = 3
    # --- asymmetric short-side overrides (None = use the long-side value) ---
    # Measured: longs and shorts hit at the same rate (26% vs 28%) but the
    # payoff ratio differs sharply (6.21 vs 1.88). A runner exit only pays when
    # winners can run, which crypto downtrends do not do, so the short side
    # gets its own exit geometry rather than inheriting the long one.
    short_stop_atr: float | None = None
    short_tp_mode: str | None = None
    short_tp_atr: tuple | None = None
    short_tp_frac: tuple | None = None
    short_max_bars: int | None = None


def _side_params(cfg: Config, side: int):
    """Effective (stop_atr, tp_mode, tp_atr, tp_frac, max_bars) for this side."""
    if side > 0:
        return cfg.stop_atr, cfg.tp_mode, cfg.tp_atr, cfg.tp_frac, cfg.max_bars
    return (cfg.short_stop_atr if cfg.short_stop_atr is not None else cfg.stop_atr,
            cfg.short_tp_mode if cfg.short_tp_mode is not None else cfg.tp_mode,
            cfg.short_tp_atr if cfg.short_tp_atr is not None else cfg.tp_atr,
            cfg.short_tp_frac if cfg.short_tp_frac is not None else cfg.tp_frac,
            cfg.short_max_bars if cfg.short_max_bars is not None else cfg.max_bars)


def _stop_dist(f: PairFeatures, i: int, cfg: Config, side: int, stop_atr: float) -> float:
    a = float(f.atr.iat[i])
    if cfg.stop_mode == "structure":
        px = f.close[i]
        lvl = float(f.swing_l.iat[i]) if side > 0 else float(f.swing_h.iat[i])
        if np.isfinite(lvl) and lvl > 0:
            d = abs(px - lvl) + 0.25 * a
            return max(d, 0.5 * a)
    return stop_atr * a


def simulate_pair(f: PairFeatures, spec: dict, cfg: Config, pair: str,
                  start: int = 250, equity_ref: float = 1000.0) -> list[Trade]:
    """One pair, one strategy. Returns closed trades."""
    long, short, score, _ = build_signals(f, spec)
    n = len(f.close)
    hi, lo, cl, op = f.high, f.low, f.close, f.open
    rsi = f.rsi.to_numpy(float)
    atr_a = f.atr.to_numpy(float)
    trend_state = f.regime["trend"].to_numpy(object)

    trades: list[Trade] = []
    i = start
    cooldown_until = 0
    liq_dist = (1.0 / cfg.leverage) * 0.9 if cfg.leverage > 1 else 10.0

    while i < n - 1:
        if i < cooldown_until or not (long[i] or short[i]):
            i += 1
            continue
        side = 1 if long[i] else -1
        s_stop, s_tpmode, s_tpatr, s_tpfrac, s_maxbars = _side_params(cfg, side)

        sd = _stop_dist(f, i, cfg, side, s_stop)
        if not np.isfinite(sd) or sd <= 0:
            i += 1
            continue

        # ---- entry (next bar open, plus slippage) ----
        base = op[i + 1]
        entry_px = base * (1 + SLIP * side)
        notional = equity_ref * cfg.stake_pct * cfg.leverage
        filled = 1.0 if cfg.entry_mode == "instant" else cfg.split_frac[0]
        pending = [] if cfg.entry_mode == "instant" else [
            (entry_px - side * cfg.split_pullback_atr * atr_a[i] * k, fr)
            for k, fr in zip((1, 2), cfg.split_frac[1:])]
        avg = entry_px
        stop = entry_px - side * sd
        tps = [entry_px + side * m * atr_a[i] for m in s_tpatr] if s_tpmode != "none" else []

        remaining = filled
        realised = 0.0
        tp_hits = 0
        funding_paid = 0.0
        be = False
        j = i + 1
        exit_reason, exit_px = "", 0.0

        while j < n:
            # staged entries fill on a touch back to the pullback level
            if pending and j - i <= cfg.split_window:
                for k, (lvl, fr) in enumerate(list(pending)):
                    touched = (lo[j] <= lvl) if side > 0 else (hi[j] >= lvl)
                    if touched:
                        px = lvl * (1 + SLIP * side)
                        avg = (avg * remaining + px * fr) / (remaining + fr)
                        remaining += fr
                        pending.remove((lvl, fr))
                        stop = avg - side * sd
                        tps = [avg + side * m * atr_a[i] for m in s_tpatr] if s_tpmode != "none" else []
            elif pending:
                pending = []

            # funding, charged on the open notional
            funding_paid += f.funding[j] * notional * remaining * side

            adverse = (avg - lo[j]) / avg if side > 0 else (hi[j] - avg) / avg
            if adverse >= liq_dist:
                exit_reason = "liquidation"
                exit_px = avg * (1 - side * liq_dist)
                break

            hit_stop = (lo[j] <= stop) if side > 0 else (hi[j] >= stop)
            if hit_stop:                      # pessimistic: stop before any TP
                exit_reason = "stop" if not be else "breakeven"
                exit_px = stop * (1 - SLIP * side)
                break

            while tp_hits < len(tps):
                lvl = tps[tp_hits]
                reached = (hi[j] >= lvl) if side > 0 else (lo[j] <= lvl)
                if not reached:
                    break
                frac = min(s_tpfrac[tp_hits], remaining)
                px = lvl * (1 - SLIP * side)
                realised += side * (px - avg) / avg * notional * frac
                realised -= (FEE * notional * frac)
                remaining -= frac
                tp_hits += 1
                if tp_hits == 1 and cfg.breakeven_after_tp1:
                    stop = avg
                    be = True
                if cfg.trail_after_tp and tp_hits >= cfg.trail_after_tp:
                    t = cl[j] - side * cfg.trail_atr * atr_a[j]
                    stop = max(stop, t) if side > 0 else min(stop, t)
                if remaining <= 1e-9:
                    break
            if remaining <= 1e-9:
                exit_reason, exit_px = "tp_ladder", cl[j]
                break

            if cfg.trail_after_tp and tp_hits >= cfg.trail_after_tp:
                t = cl[j] - side * cfg.trail_atr * atr_a[j]
                stop = max(stop, t) if side > 0 else min(stop, t)

            # oscillator exit on the remainder once TP1 is banked
            if cfg.osc_exit and tp_hits >= 1:
                opposed = (rsi[j] > 70) if side > 0 else (rsi[j] < 30)
                if opposed:
                    exit_reason, exit_px = "osc_exit", cl[j] * (1 - SLIP * side)
                    break

            # opposite signal closes the position
            if (side > 0 and short[j]) or (side < 0 and long[j]):
                exit_reason, exit_px = "reverse", cl[j] * (1 - SLIP * side)
                break

            if j - i >= s_maxbars:
                exit_reason, exit_px = "timeout", cl[j] * (1 - SLIP * side)
                break
            j += 1

        if not exit_reason:
            j = min(j, n - 1)
            exit_reason, exit_px = "eod", cl[j] * (1 - SLIP * side)

        if remaining > 1e-9:
            realised += side * (exit_px - avg) / avg * notional * remaining
            realised -= FEE * notional * remaining
        realised -= FEE * notional          # entry fee on full size
        realised -= funding_paid

        # cap the risk denominator so R stays comparable between strategies
        # that use a tight structural stop and ones that ride with a wide stop
        risk = min(sd, 5.0 * atr_a[i]) / avg * notional
        trades.append(Trade(pair=pair, side=side, entry_i=i, exit_i=j, entry=avg,
                            exit=exit_px, pnl=realised, r=realised / risk if risk else 0,
                            reason=exit_reason, tp_hits=tp_hits, score=float(score[i]),
                            bars=j - i, regime=str(trend_state[i]),
                            funding_paid=funding_paid, notional=notional))
        cooldown_until = j + cfg.cooldown
        i = max(j, i + 1)

    return trades


def simulate(universe: dict[str, PairFeatures], spec: dict, cfg: Config) -> list[Trade]:
    out = []
    for pair, f in universe.items():
        out.extend(simulate_pair(f, spec, cfg, pair))
    return out
