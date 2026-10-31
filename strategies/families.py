"""Registered families (FAMILIES.md). Each returns score(panel, t): higher = short, lower = long,
using bars < t only."""
from __future__ import annotations

import itertools

import numpy as np

from quant.panel import Panel


def funding_ls(lookback_days: int):
    """F1: short the most crowded (highest average funding), long the least."""
    n = lookback_days * 3

    def score(p: Panel, t: int) -> np.ndarray:
        if t < n:
            return np.full(p.close.shape[1], np.nan)
        f = np.where(np.isnan(p.close[t - n:t]), np.nan, p.fund[t - n:t])
        valid = (~np.isnan(f)).sum(0)
        tot = np.nansum(f, 0)
        s = np.divide(tot, valid, out=np.full_like(tot, np.nan), where=valid > 0)
        return np.where(valid >= max(1, n // 2), s, np.nan)
    return score


def reversal_ls(lookback_days: int):
    """F2: short the biggest recent winners, long the biggest recent losers."""
    n = lookback_days * 3

    def score(p: Panel, t: int) -> np.ndarray:
        if t <= n:
            return np.full(p.close.shape[1], np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            return p.close[t - 1] / p.close[t - 1 - n] - 1
    return score


def random_scores(seed: int):
    rng = np.random.default_rng(seed)

    def score(p: Panel, t: int) -> np.ndarray:
        return rng.random(p.close.shape[1])
    return score


def _vol_groups(p: Panel, t: int, ok: np.ndarray, k: int) -> list[np.ndarray]:
    """Eligible coins sorted by 30-day volatility of 8h log returns, cut into k equal groups."""
    idx = np.where(ok)[0]
    with np.errstate(invalid="ignore", divide="ignore"):
        lr = np.diff(np.log(p.close[max(0, t - 91):t, idx]), axis=0)
    vol = np.nanstd(lr, axis=0)
    order = idx[np.argsort(vol, kind="stable")]
    return [g for g in np.array_split(order, k) if len(g) >= 2]


def funding_pairs(lookback_days: int):
    """F3: inside each volatility group, long the lowest-funding coin, short the highest."""
    base = funding_ls(lookback_days)

    def score(p: Panel, t: int) -> np.ndarray:
        return base(p, t)

    def pick(p: Panel, t: int, ok: np.ndarray, k: int, q=None):
        s = base(p, t)
        longs, shorts = [], []
        for g in _vol_groups(p, t, ok, k):
            longs.append(g[np.argmin(s[g])])
            shorts.append(g[np.argmax(s[g])])
        return np.array(longs, int), np.array(shorts, int)
    score.pick = pick
    return score


def random_pairs(seed: int):
    """F3 twin: same volatility groups, random long and short inside each."""
    rng = np.random.default_rng(seed)

    def score(p: Panel, t: int) -> np.ndarray:
        return np.zeros(p.close.shape[1])

    def pick(p: Panel, t: int, ok: np.ndarray, k: int, q=None):
        longs, shorts = [], []
        for g in _vol_groups(p, t, ok, k):
            a, b = rng.choice(g, 2, replace=False)
            longs.append(a)
            shorts.append(b)
        return np.array(longs, int), np.array(shorts, int)
    score.pick = pick
    return score


def _trend20(p: Panel, t: int) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        return p.close[t - 1] / p.close[t - 61] - 1 if t > 61 else np.full(p.close.shape[1], np.nan)


def _split_pick(s: np.ndarray, ok: np.ndarray, short_ok: np.ndarray, k: int):
    idx = np.where(ok)[0]
    longs = idx[np.argsort(s[idx], kind="stable")][:k]
    cand = np.where(ok & short_ok)[0]
    cand = cand[~np.isin(cand, longs)]
    shorts = cand[np.argsort(-s[cand], kind="stable")][:k]
    n = min(len(longs), len(shorts))
    return longs[:n], shorts[:n]


def funding_trendbreak(lookback_days: int):
    """F5: long the lowest funding; short the highest funding among coins whose 20-day change <= 0."""
    base = funding_ls(lookback_days)

    def score(p: Panel, t: int) -> np.ndarray:
        return base(p, t)

    def pick(p: Panel, t: int, ok: np.ndarray, k: int, q=None):
        return _split_pick(base(p, t), ok, _trend20(p, t) <= 0, k)
    score.pick = pick
    return score


def random_trendbreak(seed: int):
    rng = np.random.default_rng(seed)

    def score(p: Panel, t: int) -> np.ndarray:
        return np.zeros(p.close.shape[1])

    def pick(p: Panel, t: int, ok: np.ndarray, k: int, q=None):
        return _split_pick(rng.random(p.close.shape[1]), ok, _trend20(p, t) <= 0, k)
    score.pick = pick
    return score


# ------------------------------------------------------------------ round 2 (F6-F8)
def band_pick(s_long, s_short, long_ok, short_ok, k: int, q):
    """Keep current positions still ranked inside the best 2k of their side; fill with the best new ones.
    Low s_long = best long, high s_short = best short. Sides disjoint and equal in count."""
    cur_l = set(np.where(q > 0)[0]) if q is not None else set()
    cur_s = set(np.where(q < 0)[0]) if q is not None else set()
    lc = np.where(long_ok & ~np.isnan(s_long))[0]
    sc = np.where(short_ok & ~np.isnan(s_short))[0]
    lo = list(lc[np.argsort(s_long[lc], kind="stable")])
    so = list(sc[np.argsort(-s_short[sc], kind="stable")])
    longs = [j for j in lo[:2 * k] if j in cur_l][:k]
    shorts = [j for j in so[:2 * k] if j in cur_s and j not in longs][:k]
    for j in lo:
        if len(longs) >= k:
            break
        if j not in longs and j not in shorts:
            longs.append(j)
    for j in so:
        if len(shorts) >= k:
            break
        if j not in shorts and j not in longs:
            shorts.append(j)
    n = min(len(longs), len(shorts))
    rl = {j: i for i, j in enumerate(lo)}
    rs = {j: i for i, j in enumerate(so)}
    longs = sorted(longs, key=rl.get)[:n]
    shorts = sorted(shorts, key=rs.get)[:n]
    return np.array(longs, int), np.array(shorts, int)


def _pct_rank(x: np.ndarray) -> np.ndarray:
    out = np.full_like(x, np.nan)
    m = ~np.isnan(x)
    if m.sum() > 1:
        out[m] = np.argsort(np.argsort(x[m], kind="stable"), kind="stable") / (m.sum() - 1)
    return out


def carry_momentum(mom_days: int):
    """F6: score = rank(7-day funding) - rank(mom_days price change); high = short."""
    fund7 = funding_ls(7)
    n = mom_days * 3

    def score(p: Panel, t: int) -> np.ndarray:
        if t <= n:
            return np.full(p.close.shape[1], np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            mom = p.close[t - 1] / p.close[t - 1 - n] - 1
        return _pct_rank(fund7(p, t)) - _pct_rank(mom)

    def pick(p: Panel, t: int, ok: np.ndarray, k: int, q=None):
        sc = score(p, t)
        return band_pick(sc, sc, ok, ok, k, q)
    score.pick = pick
    return score


def residual_reversal(lookback_days: int):
    """F7: residual (market beta removed) return over the lookback; short highest, long lowest."""
    n = lookback_days * 3

    def score(p: Panel, t: int) -> np.ndarray:
        N = p.close.shape[1]
        if t < 92:
            return np.full(N, np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            R = np.diff(np.log(p.close[t - 91:t]), axis=0)          # [90, N] 8h log returns
            mkt = np.nanmean(R, axis=1)                             # equal-weight market
        w = (~np.isnan(R)).astype(float)
        good = w.sum(0) >= 80
        Rz = np.where(np.isnan(R), 0.0, R)
        mkt = np.where(np.isnan(mkt), 0.0, mkt)
        mc = mkt - mkt.mean()
        beta = (w * Rz * mc[:, None]).sum(0) / np.maximum((w * mc[:, None] ** 2).sum(0), 1e-12)
        res = ((Rz[-n:] - beta * mkt[-n:, None]) * w[-n:]).sum(0)
        return np.where(good & ~np.isnan(p.close[t - 1]), res, np.nan)

    def pick(p: Panel, t: int, ok: np.ndarray, k: int, q=None):
        sc = score(p, t)
        return band_pick(sc, sc, ok, ok, k, q)
    score.pick = pick
    return score


_FIRST: dict = {}


def _first_bar(p: Panel) -> np.ndarray:
    key = id(p.close)
    if key not in _FIRST:
        alive = ~np.isnan(p.close)
        _FIRST[key] = np.where(alive.any(0), alive.argmax(0), 10**9)
    return _FIRST[key]


def listing_fade(max_age_days: int):
    """F8: short coins listed <= max_age_days ago (newest first); long the most-traded coins older than 1 year."""
    def score(p: Panel, t: int) -> np.ndarray:
        return np.zeros(p.close.shape[1])

    def pick(p: Panel, t: int, ok: np.ndarray, k: int, q=None):
        age = (t - _first_bar(p)) / 3.0
        vol30 = np.nansum(p.qvol[max(0, t - 90):t], 0)
        return band_pick(-vol30, -age, ok & (age > 365), ok & (age <= max_age_days), k, q)
    score.pick = pick
    return score


def random_band(seed: int):
    """Twin for F6/F7: random ranks, same holding band (same turnover style)."""
    rng = np.random.default_rng(seed)

    def score(p: Panel, t: int) -> np.ndarray:
        return np.zeros(p.close.shape[1])

    def pick(p: Panel, t: int, ok: np.ndarray, k: int, q=None):
        sc = rng.random(p.close.shape[1])
        return band_pick(sc, sc, ok, ok, k, q)
    score.pick = pick
    return score


def random_listing(max_age_days: int):
    """Twin for F8: random established coins long, random coins short (no age rule), same band."""
    def maker(seed: int):
        rng = np.random.default_rng(seed)

        def score(p: Panel, t: int) -> np.ndarray:
            return np.zeros(p.close.shape[1])

        def pick(p: Panel, t: int, ok: np.ndarray, k: int, q=None):
            age = (t - _first_bar(p)) / 3.0
            sc = rng.random(p.close.shape[1])
            return band_pick(sc, sc, ok & (age > 365), ok, k, q)
        score.pick = pick
        return score
    return maker


def size_ls(lookback_days: int):
    """F12: long the k most-traded coins, short the k least-traded (eligible ones only)."""
    n = lookback_days * 3

    def score(p: Panel, t: int) -> np.ndarray:
        if t < n:
            return np.full(p.close.shape[1], np.nan)
        return -np.nansum(p.qvol[t - n:t], 0)            # high volume -> low score -> long

    def pick(p: Panel, t: int, ok: np.ndarray, k: int, q=None):
        sc = score(p, t)
        return band_pick(sc, sc, ok, ok, k, q)
    score.pick = pick
    return score


def size_carry(vol_days: int):
    """F13: score = rank(7-day funding) - rank(vol_days traded volume); high = short."""
    fund7 = funding_ls(7)
    n = vol_days * 3

    def score(p: Panel, t: int) -> np.ndarray:
        if t < n:
            return np.full(p.close.shape[1], np.nan)
        vol = np.nansum(p.qvol[t - n:t], 0)
        vol = np.where(np.isnan(p.close[t - 1]), np.nan, vol)
        return _pct_rank(fund7(p, t)) - _pct_rank(vol)

    def pick(p: Panel, t: int, ok: np.ndarray, k: int, q=None):
        sc = score(p, t)
        return band_pick(sc, sc, ok, ok, k, q)
    score.pick = pick
    return score


def attention_reversal(lookback_days: int):
    """F14: short the k most-traded coins, long the k least-traded."""
    n = lookback_days * 3

    def score(p: Panel, t: int) -> np.ndarray:
        if t < n:
            return np.full(p.close.shape[1], np.nan)
        return np.nansum(p.qvol[t - n:t], 0)              # high volume -> high score -> short

    def pick(p: Panel, t: int, ok: np.ndarray, k: int, q=None):
        sc = score(p, t)
        return band_pick(sc, sc, ok, ok, k, q)
    score.pick = pick
    return score


def crowding_attention(vol_days: int):
    """F15: score = rank(7-day funding) + rank(vol_days traded volume); high = short."""
    fund7 = funding_ls(7)
    n = vol_days * 3

    def score(p: Panel, t: int) -> np.ndarray:
        if t < n:
            return np.full(p.close.shape[1], np.nan)
        vol = np.where(np.isnan(p.close[t - 1]), np.nan, np.nansum(p.qvol[t - n:t], 0))
        return _pct_rank(fund7(p, t)) + _pct_rank(vol)

    def pick(p: Panel, t: int, ok: np.ndarray, k: int, q=None):
        sc = score(p, t)
        return band_pick(sc, sc, ok, ok, k, q)
    score.pick = pick
    return score


# ------------------------------------------------------------------ Protocol B (positioning, 4h bars)
def _z(x: np.ndarray, t: int, lb: int, win: int) -> np.ndarray:
    """(mean of x over the last lb bars - its mean over win bars) / its std over win bars."""
    if t < win:
        return np.full(x.shape[1], np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        hist = x[t - win:t]
        mu, sd = np.nanmean(hist, 0), np.nanstd(hist, 0)
        cur = np.nanmean(x[t - lb:t], 0)
        return np.where(sd > 0, (cur - mu) / sd, np.nan)


def _pos_family(fn):
    def make(lookback_days: int):
        def score(p: Panel, t: int) -> np.ndarray:
            return fn(p, t, lookback_days * p.bars_per_day, 30 * p.bars_per_day)

        def pick(p: Panel, t: int, ok: np.ndarray, k: int, q=None):
            sc = score(p, t)
            return band_pick(sc, sc, ok, ok, k, q)
        score.pick = pick
        return score
    return make


retail_contrarian = _pos_family(lambda p, t, lb, win: _z(p.feat["global_ls"], t, lb, win))
smart_vs_retail = _pos_family(lambda p, t, lb, win: _z(p.feat["global_ls"], t, lb, win)
                              - _z(p.feat["top_ls_positions"], t, lb, win))
taker_exhaustion = _pos_family(lambda p, t, lb, win: _z(p.feat["taker_ls"], t, lb, win))


def _crowded_chase(p: Panel, t: int, lb: int, win: int) -> np.ndarray:
    if t <= lb:
        return np.full(p.close.shape[1], np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        doi = p.feat["oi"][t - 1] / p.feat["oi"][t - 1 - lb] - 1
        dpx = p.close[t - 1] / p.close[t - 1 - lb] - 1
    return _pct_rank(doi) + _pct_rank(dpx)


crowded_chase = _pos_family(_crowded_chase)
GRID_B = {"k": [3, 5], "lookback_days": [1, 3, 7], "every": [6, 42]}


GRID_A = {"k": [3, 5, 8], "lookback_days": [1, 3, 7], "every": [1, 3]}     # every: 8h bars -> 8h / 24h
GRID_F3 = {"k": [5, 8, 12], "lookback_days": [3, 7, 14], "every": [1, 3]}

FAMILIES = {
    "F1": {"name": "funding_ls", "make": funding_ls, "grid": GRID_A, "twin": random_scores},
    "F2": {"name": "reversal_ls", "make": reversal_ls, "grid": GRID_A, "twin": random_scores},
    "F3": {"name": "funding_pairs", "make": funding_pairs, "grid": GRID_F3, "twin": random_pairs},
    "F4": {"name": "funding_ls_voltarget", "make": funding_ls, "grid": GRID_A, "twin": random_scores,
           "vol_target": 0.25, "lev_cap": 5.0},
    "F5": {"name": "funding_trendbreak", "make": funding_trendbreak, "grid": GRID_A, "twin": random_trendbreak},
    "F6": {"name": "carry_momentum", "make": carry_momentum, "twin": random_band,
           "grid": {"k": [5, 8, 12], "lookback_days": [14, 30], "every": [3, 21]}},
    "F7": {"name": "residual_reversal", "make": residual_reversal, "twin": random_band,
           "grid": {"k": [5, 8, 12], "lookback_days": [1, 3], "every": [1, 3]}},
    "F9": {"name": "carry_momentum_stop", "make": carry_momentum, "twin": random_band, "stop": 0.30,
           "grid": {"k": [5, 8, 12], "lookback_days": [14, 30], "every": [3, 21]}},
    "F10": {"name": "funding_ls_all", "make": funding_ls, "grid": GRID_A, "twin": random_scores, "universe": "all"},
    "F11": {"name": "listing_fade_all", "make": listing_fade, "twin_cfg": random_listing, "universe": "all",
            "grid": {"k": [3, 5, 8], "lookback_days": [60, 180], "every": [3, 21]}},
    "F12": {"name": "size_ls", "make": size_ls, "twin": random_band, "universe": "all",
            "grid": {"k": [5, 8, 12], "lookback_days": [7, 30], "every": [3, 21]}},
    "F13": {"name": "size_carry", "make": size_carry, "twin": random_band, "universe": "all",
            "grid": {"k": [5, 8, 12], "lookback_days": [7, 30], "every": [3, 21]}},
    "F14": {"name": "attention_reversal", "make": attention_reversal, "twin": random_band, "universe": "all",
            "grid": {"k": [5, 8, 12], "lookback_days": [7, 30], "every": [3, 21]}},
    "F15": {"name": "crowding_attention", "make": crowding_attention, "twin": random_band, "universe": "all",
            "grid": {"k": [5, 8, 12], "lookback_days": [7, 30], "every": [3, 21]}},
    "F16": {"name": "attention_reversal_stop", "make": attention_reversal, "twin": random_band, "universe": "all",
            "stop": 0.30, "grid": {"k": [5, 8, 12], "lookback_days": [7, 30], "every": [3, 21]}},
    "F17": {"name": "crowding_attention_stop", "make": crowding_attention, "twin": random_band, "universe": "all",
            "stop": 0.30, "grid": {"k": [5, 8, 12], "lookback_days": [7, 30], "every": [3, 21]}},
    "P1": {"name": "retail_contrarian", "make": retail_contrarian, "twin": random_band, "universe": "pos", "grid": GRID_B},
    "P2": {"name": "smart_vs_retail", "make": smart_vs_retail, "twin": random_band, "universe": "pos", "grid": GRID_B},
    "P3": {"name": "crowded_chase", "make": crowded_chase, "twin": random_band, "universe": "pos", "grid": GRID_B},
    "P4": {"name": "taker_exhaustion", "make": taker_exhaustion, "twin": random_band, "universe": "pos", "grid": GRID_B},
    "F8": {"name": "listing_fade", "make": listing_fade, "twin_cfg": random_listing,
           "grid": {"k": [3, 5, 8], "lookback_days": [60, 180], "every": [3, 21]}},
}


def grid(g: dict):
    for k, lb, ev in itertools.product(g["k"], g["lookback_days"], g["every"]):
        yield {"k": k, "lookback_days": lb, "every": ev}


def neighbours(g: dict, cfg: dict) -> list[dict]:
    out = []
    for key, vals in g.items():
        i = vals.index(cfg[key])
        for j in (i - 1, i + 1):
            if 0 <= j < len(vals):
                out.append({**cfg, key: vals[j]})
    return out
