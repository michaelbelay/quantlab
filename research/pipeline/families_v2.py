"""New strategy families for the research pipeline (2026-10-04).

Each one tests a market behaviour that none of the 32 engine families targets directly.
They plug into the engine's FAMILIES table, so the same backtester, costs and filters apply.
Every signal uses only closed bars (shifted where a value is formed on the current bar).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import signals as S
from features import PairFeatures, load_pair


def _shift(x, k=1):
    return np.asarray(pd.Series(np.asarray(x, dtype=bool)).shift(k).fillna(False), dtype=bool)


def f_funding_extreme(f: PairFeatures, p: dict):
    """Fade the crowded side when perpetual funding is extreme.

    Hypothesis: when funding is far above its own recent norm, leveraged longs are crowded
    and pay to stay in; crowded positioning tends to unwind, so price drifts against them.
    Entry: funding z-score (30-day window) above +z -> short; below -z -> long.
    """
    z = float(p.get("z", 2.5))
    fund = pd.Series(f.funding)
    mu, sd = fund.rolling(720, min_periods=240).mean(), fund.rolling(720, min_periods=240).std()
    zs = ((fund - mu) / sd.replace(0, np.nan)).fillna(0).shift(1).fillna(0).to_numpy()
    return zs < -z, zs > z, {"funding_z": S._norm(pd.Series(np.abs(zs)), z, z * 2)}


def f_structure_break(f: PairFeatures, p: dict):
    """Market structure: break of the last confirmed swing high after a higher low.

    Hypothesis: a higher low followed by a break of the prior swing high marks a change in
    who controls the market; continuation follows more often than reversal.
    Entry long: swing low rising over `lookback` bars and close crosses above the last
    confirmed swing high. Mirror for shorts.
    """
    lb = int(p.get("lookback", 50))
    sh, sl = f.swing_h, f.swing_l
    c = pd.Series(f.close)
    hl = (sl > sl.shift(lb)).to_numpy()
    lh = (sh < sh.shift(lb)).to_numpy()
    up = ((c > sh) & (c.shift(1) <= sh.shift(1))).to_numpy()
    dn = ((c < sl) & (c.shift(1) >= sl.shift(1))).to_numpy()
    return up & hl, dn & lh, {"structure": np.full(len(c), 0.6)}


def f_rel_strength(f: PairFeatures, p: dict):
    """Relative strength against BTC.

    Hypothesis: coins outperforming BTC while in their own uptrend attract flow (rotation
    into leaders); persistent laggards in downtrends keep lagging.
    Entry long: coin's n-bar return minus BTC's n-bar return > thr and close > EMA200.
    """
    n, thr = int(p.get("n", 72)), float(p.get("thr", 0.05))
    b = load_pair("BTC")
    c = pd.Series(f.close, index=pd.Index(f.date))
    rc = c / c.shift(n) - 1
    if b is None:
        rb = pd.Series(0.0, index=c.index)
    else:
        bc = pd.Series(b.close, index=pd.Index(b.date))
        rb = (bc / bc.shift(n) - 1).reindex(c.index, method="ffill").fillna(0)
    rs = (rc - rb).shift(1).fillna(0).to_numpy()
    above = f.close > f.ema_200.to_numpy()
    return (rs > thr) & above, (rs < -thr) & ~above, {"rel_strength": S._norm(pd.Series(np.abs(rs)), thr, thr * 3)}


def f_regime_switch(f: PairFeatures, p: dict):
    """Regime-adaptive: trend-following in trends, mean reversion in ranges.

    Hypothesis: neither style works everywhere; switching on a measured regime (ADX)
    keeps each style where its edge should exist.
    Entry: trend_continuation signals when ADX > 25; mean_reversion signals when ADX < 18.
    """
    tl, ts, _ = S.FAMILIES["trend_continuation"](f, p)
    ml, ms, _ = S.FAMILIES["mean_reversion"](f, p)
    adx = f.adx.to_numpy()
    trend, rng = adx > float(p.get("adx_hi", 25)), adx < float(p.get("adx_lo", 18))
    return (tl & trend) | (ml & rng), (ts & trend) | (ms & rng), {"adx": S._norm(f.adx, 15, 40)}


def f_combo(f: PairFeatures, p: dict):
    """Two independent signals agreeing.

    Hypothesis: two signals built from different information (e.g. price structure and
    volume, or momentum and volatility) agreeing within a short window are more reliable
    than either alone.
    Entry: family `a` fires and family `b` fired in the same direction within `window` bars.
    """
    a, b, w = p["a"], p["b"], int(p.get("window", 6))
    al, as_, _ = S.FAMILIES[a](f, p.get("pa", {}))
    bl, bs, _ = S.FAMILIES[b](f, p.get("pb", {}))
    roll = lambda m: np.asarray(pd.Series(np.asarray(m, dtype=float)).rolling(w, min_periods=1).max() > 0)
    return np.asarray(al, bool) & roll(bl), np.asarray(as_, bool) & roll(bs), {"combo": np.full(len(f.close), 0.7)}


NEW = {
    "funding_extreme": f_funding_extreme,
    "structure_break": f_structure_break,
    "rel_strength": f_rel_strength,
    "regime_switch": f_regime_switch,
    "combo": f_combo,
}
S.FAMILIES.update(NEW)
S.COUNTER_TREND.add("funding_extreme")
