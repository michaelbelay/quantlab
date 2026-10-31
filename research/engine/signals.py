"""Strategy family library and the modular filter engine.

Each family returns raw (long, short) trigger arrays plus named component
scores. Families never decide to trade on their own -- triggers are gated by
filters and combined into a confidence score, so a breakout in a dead market
and a breakout with volume expansion are not treated alike.

Adding family #16 means adding one function and one FAMILIES entry.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from features import PairFeatures, atr, load_pair


def btc_regime(n: int, dates) -> np.ndarray:
    """Market-wide regime: is BTC above its own long trend?

    Aligned by timestamp and shifted one bar, so a decision at bar i only uses
    BTC data that had already closed. This market-wide gate (rather than a
    per-pair one) was the decisive ingredient in the earlier surviving strategy.
    """
    b = load_pair("BTC")
    if b is None:
        return np.ones(n, dtype=bool)
    s = pd.Series(np.asarray(b.close > b.ema_200.to_numpy()), index=pd.Index(b.date))
    return s.shift(1).fillna(False).reindex(pd.Index(dates), method="ffill") \
            .fillna(False).to_numpy(bool)


def _s(x) -> np.ndarray:
    return np.asarray(x, dtype=bool)


def _norm(x: pd.Series, lo: float, hi: float) -> np.ndarray:
    """Squash a series into 0..1 for scoring."""
    return np.clip((np.asarray(x, dtype=float) - lo) / (hi - lo + 1e-12), 0, 1)


# --------------------------------------------------------------------------
# Strategy families. Each: (features, params) -> (long, short, scores)
# --------------------------------------------------------------------------

def _levels(f: PairFeatures, n: int):
    """Rolling breakout levels, cached; computed on demand for any lookback."""
    key = f"_lv{n}"
    if not hasattr(f, key):
        hh = f.df["high"].rolling(n).max().shift(1).to_numpy(float)
        ll = f.df["low"].rolling(n).min().shift(1).to_numpy(float)
        setattr(f, key, (hh, ll))
    return getattr(f, key)


def f_breakout(f: PairFeatures, p: dict):
    n = p.get("lookback", 20)
    hh, ll = _levels(f, n)
    long = f.close > hh
    short = f.close < ll
    strength = _norm((f.close - hh) / f.atr.replace(0, np.nan), 0, 1.5)
    strength_s = _norm((ll - f.close) / f.atr.replace(0, np.nan), 0, 1.5)
    return _s(long), _s(short), {"breakout": np.where(long, strength, strength_s)}


def f_range_breakout(f: PairFeatures, p: dict):
    """Breakout specifically out of a tight range (squeeze -> expansion)."""
    tight = _s(f.squeeze < p.get("squeeze_max", 0.8))
    hh = f.hh20.to_numpy(float)
    ll = f.ll20.to_numpy(float)
    long = tight & (f.close > hh)
    short = tight & (f.close < ll)
    sc = _norm(1 / f.squeeze.replace(0, np.nan), 0.8, 2.0)
    return _s(long), _s(short), {"squeeze": sc}


def f_trend_continuation(f: PairFeatures, p: dict):
    up = _s(f.ema_fast > f.ema_slow) & _s(f.close > f.ema_200)
    dn = _s(f.ema_fast < f.ema_slow) & _s(f.close < f.ema_200)
    cross_up = up & ~np.r_[False, up[:-1]]
    cross_dn = dn & ~np.r_[False, dn[:-1]]
    return cross_up, cross_dn, {"trend": _norm(f.adx, 15, 40)}


def f_pullback(f: PairFeatures, p: dict):
    """Buy a dip to the fast EMA inside an established uptrend (mirror short)."""
    k = p.get("depth_atr", 0.5)
    up = _s(f.ema_fast > f.ema_slow) & _s(f.close > f.ema_200)
    dn = _s(f.ema_fast < f.ema_slow) & _s(f.close < f.ema_200)
    near = np.asarray((f.close - f.ema_fast).abs() / f.atr.replace(0, np.nan) < k)
    touched_dn = np.asarray(f.low <= f.ema_fast.to_numpy())
    touched_up = np.asarray(f.high >= f.ema_fast.to_numpy())
    return up & near & touched_dn, dn & near & touched_up, {"trend": _norm(f.adx, 15, 40)}


def f_mean_reversion(f: PairFeatures, p: dict):
    lo, hi = p.get("rsi_lo", 30), p.get("rsi_hi", 70)
    long = _s(f.rsi < lo)
    short = _s(f.rsi > hi)
    return long, short, {"oscillator": np.where(long, _norm(lo - f.rsi, 0, 15),
                                                _norm(f.rsi - hi, 0, 15))}


def f_channel(f: PairFeatures, p: dict):
    long = _s(f.close <= f.bb_dn)
    short = _s(f.close >= f.bb_up)
    width = _norm(f.bb_width, 0.02, 0.12)
    return long, short, {"channel": width}


def f_sr_rejection(f: PairFeatures, p: dict):
    """Wick rejection at a confirmed swing level."""
    k = p.get("tol_atr", 0.35)
    a = f.atr.replace(0, np.nan).to_numpy(float)
    sl = f.swing_l.to_numpy(float)
    sh = f.swing_h.to_numpy(float)
    at_sup = np.abs(f.low - sl) / a < k
    at_res = np.abs(f.high - sh) / a < k
    bull_bar = f.close > f.open
    bear_bar = f.close < f.open
    return _s(at_sup & bull_bar), _s(at_res & bear_bar), {"sr": np.full(len(a), 0.7)}


def f_momentum(f: PairFeatures, p: dict):
    th = p.get("mom_th", 0.03)
    long = _s(f.mom > th)
    short = _s(f.mom < -th)
    return long, short, {"momentum": _norm(f.mom.abs(), th, th * 4)}


def f_vol_expansion(f: PairFeatures, p: dict):
    exp = _s(f.vol_expand > p.get("exp_th", 1.3))
    long = exp & _s(f.close > f.ema_fast)
    short = exp & _s(f.close < f.ema_fast)
    return long, short, {"volatility": _norm(f.vol_expand, 1.2, 2.0)}


def f_vol_contraction_break(f: PairFeatures, p: dict):
    """Contraction then a directional push -- the classic coil."""
    coil = _s(f.squeeze < 0.7) & _s(f.vol_expand > 1.2)
    long = coil & _s(f.close > f.bb_mid)
    short = coil & _s(f.close < f.bb_mid)
    return long, short, {"squeeze": _norm(1 / f.squeeze.replace(0, np.nan), 1.2, 2.5)}


def f_trendline_bounce(f: PairFeatures, p: dict):
    """Price returns to a rising/falling structural line and rejects it."""
    rising = _s(f.tl_slope > p.get("tl_th", 0.5))
    falling = _s(f.tl_slope < -p.get("tl_th", 0.5))
    near = np.asarray((f.close - f.ema_slow).abs() / f.atr.replace(0, np.nan) < 0.6)
    return rising & near, falling & near, {"trendline": _norm(f.tl_slope.abs(), 0.3, 2.0)}


def f_reentry_pullback(f: PairFeatures, p: dict):
    """Re-entry: trend intact, price pulled back and is resuming."""
    up = _s(f.ema_fast > f.ema_slow)
    dn = ~up
    dipped = _s(f.rsi.shift(1) < 45) & _s(f.rsi > 45)
    popped = _s(f.rsi.shift(1) > 55) & _s(f.rsi < 55)
    return up & dipped, dn & popped, {"trend": _norm(f.adx, 15, 40)}


def f_reversal(f: PairFeatures, p: dict):
    """Exhaustion reversal: extreme move into a level, then a turn."""
    ext_dn = _s(f.close <= f.ll55) & _s(f.rsi < 30)
    ext_up = _s(f.close >= f.hh55) & _s(f.rsi > 70)
    turn_up = _s(f.close > f.open)
    turn_dn = _s(f.close < f.open)
    return ext_dn & turn_up, ext_up & turn_dn, {"oscillator": np.full(len(f.close), 0.6)}


def f_rsi_divergence(f: PairFeatures, p: dict):
    return _s(f.div_bull), _s(f.div_bear), {"divergence": np.full(len(f.close), 0.75)}


def f_breakout_retest(f: PairFeatures, p: dict):
    """Break a level, come back to it, hold -- entry on the hold."""
    win = p.get("retest_win", 12)
    hh = f.hh20.to_numpy(float)
    ll = f.ll20.to_numpy(float)
    broke_up = pd.Series(f.close > hh).rolling(win).max().fillna(0).to_numpy(bool)
    broke_dn = pd.Series(f.close < ll).rolling(win).max().fillna(0).to_numpy(bool)
    a = f.atr.replace(0, np.nan).to_numpy(float)
    back_up = np.abs(f.low - hh) / a < 0.5
    back_dn = np.abs(f.high - ll) / a < 0.5
    hold_up = f.close > f.open
    hold_dn = f.close < f.open
    return _s(broke_up & back_up & hold_up), _s(broke_dn & back_dn & hold_dn), \
        {"breakout": np.full(len(a), 0.65), "sr": np.full(len(a), 0.7)}


def f_volatility_breakout(f: PairFeatures, p: dict):
    """Wilder volatility system: a bar whose move exceeds k*ATR carries on.

    This is the family that survived the earlier research phase, included so the
    tournament is benchmarked against a known-good baseline rather than only
    against its own inventions. `bars` resamples the 1h series to a slower clock.
    """
    bars = int(p.get("bars", 3))
    mult = float(p.get("atr_mult", 2.5))
    key = f"_vb{bars}_{mult}"
    if not hasattr(f, key):
        d = f.df
        # Block boundaries are ABSOLUTE wall-clock windows, not row positions.
        # Positional grouping (d.index // bars) silently desynchronises the moment
        # two systems hold different row counts for the same span: the dev coins
        # are missing 14 candles from the 2021-02-11 Binance outage, the old backtester
        # fills them (converter.ohlcv_fill_up_missing_data) and the engine does
        # not, so every block after that gap landed on different bars in the two
        # systems. Grouping on the timestamp makes a "2-hour block" the same two
        # hours everywhere, regardless of gaps, fill policy or start date.
        _dt = pd.to_datetime(d["date"], utc=True)
        _step = _dt.diff().median()          # the data's own bar interval
        g = pd.Series(
            (_dt - pd.Timestamp("1970-01-01", tz="UTC")) // (_step * bars),
            index=d.index,
        )
        agg = d.groupby(g).agg(high=("high", "max"), low=("low", "min"),
                               close=("close", "last"), open=("open", "first"))
        a = atr(agg, 14) * mult
        chg = agg["close"].diff()
        # A block's close is only known once the block ENDS. Acting on block k
        # at the first bar of block k would be lookahead, so the decision for
        # block k uses block k-1's completed move against block k-2's ATR.
        up_blk = (chg.shift(1) > a.shift(2))
        dn_blk = ((-chg.shift(1)) > a.shift(2))
        up = up_blk.reindex(g).to_numpy(bool)
        dn = dn_blk.reindex(g).to_numpy(bool)
        blk_start = np.r_[True, g.values[1:] != g.values[:-1]]
        setattr(f, key, (up & blk_start, dn & blk_start))
    long, short = getattr(f, key)
    return _s(long), _s(short), {"volatility": _norm(f.vol_expand, 0.9, 1.6)}


# --------------------------------------------------------------------------
# Families harvested from GreenAgent (2026-09-21). GreenAgent embedded entry,
# stop, target, hold limit and cooldown in one loop; only the ENTRY hypothesis
# is taken here, so the engine's own exit geometry, cost model, holdout coins
# and 2x-cost test apply to them for the first time. GreenAgent's own 12-window
# walk-forward scored these negative, but with no coin holdout, no cost
# doubling and no parameter-neighbour test -- so they are re-opened, not
# re-asserted.
# --------------------------------------------------------------------------

def f_trend_resume(f: PairFeatures, p: dict):
    """Resumption AFTER a shallow pullback, not the pullback itself.

    GreenAgent swing_trend_continuation. Distinct from f_pullback, which tests
    that price is near the fast EMA right now: this requires the touch to have
    happened within the last `pullback_window` bars and price to have already
    resumed back through the EMA on a candle that closes in the trend's
    direction. The trigger is the resumption bar.
    """
    look = int(p.get("slope_lookback", 5))
    pw = int(p.get("pullback_window", 5))
    vmult = float(p.get("vol_mult", 0.8))
    d = f.df
    c, o, hi, lo = d["close"], d["open"], d["high"], d["low"]
    fast, slow = f.ema_fast, f.ema_slow

    slope_up = _s(fast > fast.shift(look))
    slope_dn = _s(fast < fast.shift(look))
    # the touch must be in the recent past, not on the trigger bar itself
    touched_dn = _s(((lo <= fast) | (c <= fast)).shift(1)
                    .rolling(pw, min_periods=1).max().fillna(0).astype(bool))
    touched_up = _s(((hi >= fast) | (c >= fast)).shift(1)
                    .rolling(pw, min_periods=1).max().fillna(0).astype(bool))
    vol_ok = _s(f.vol_rel >= vmult)

    long = (slope_up & _s(c > slow) & _s(c > fast) & touched_dn & _s(c > o)
            & _s((f.rsi >= p.get("rsi_long_lo", 42.0))
                 & (f.rsi <= p.get("rsi_long_hi", 68.0))) & vol_ok)
    short = (slope_dn & _s(c < slow) & _s(c < fast) & touched_up & _s(c < o)
             & _s((f.rsi >= p.get("rsi_short_lo", 32.0))
                  & (f.rsi <= p.get("rsi_short_hi", 58.0))) & vol_ok)
    return long, short, {"trend": _norm(f.adx, 15, 40)}


def f_rsi_reset(f: PairFeatures, p: dict):
    """Oscillator dip-and-recover inside a trend.

    GreenAgent intraday_ema_retest. The engine had no "was below X, now
    recovered into a band" mechanism -- every existing oscillator family tests
    only the current reading. Here the reset is the setup and the recovery is
    the trigger.
    """
    look = int(p.get("slope_lookback", 5))
    pl = int(p.get("pullback_lookback", 6))
    vmult = float(p.get("vol_mult", 0.8))
    d = f.df
    c, o = d["close"], d["open"]
    fast, slow = f.ema_fast, f.ema_slow

    slope_up = _s(slow > slow.shift(look))
    slope_dn = _s(slow < slow.shift(look))
    dipped = _s((f.rsi < p.get("dip_long", 52.0)).shift(1)
                .rolling(pl, min_periods=1).max().fillna(0).astype(bool))
    popped = _s((f.rsi > p.get("dip_short", 48.0)).shift(1)
                .rolling(pl, min_periods=1).max().fillna(0).astype(bool))
    vol_ok = _s(f.vol_rel >= vmult)
    resuming_up = _s(c > c.shift(1))
    resuming_dn = _s(c < c.shift(1))

    long = (slope_up & _s(c > slow) & _s(c > fast) & dipped & resuming_up
            & _s((f.rsi >= p.get("rec_lo", 46.0))
                 & (f.rsi <= p.get("rec_hi", 65.0))) & vol_ok)
    short = (slope_dn & _s(c < slow) & _s(c < fast) & popped & resuming_dn
             & _s((f.rsi >= p.get("rec_s_lo", 35.0))
                  & (f.rsi <= p.get("rec_s_hi", 54.0))) & vol_ok)
    return long, short, {"trend": _norm(f.adx, 15, 40)}


def f_band_fade_confirmed(f: PairFeatures, p: dict):
    """Band touch ARMS the trade; an opposing candle TRIGGERS it.

    GreenAgent downtrend_fade. f_channel fires on the band touch itself; this
    waits for the reversal to show itself, which is the whole point of the
    original ("a touch only *arms* a short -- bearish confirmation is
    required"). Symmetric here; direction gating is left to the filters.
    """
    aw = int(p.get("arm_window", 3))
    d = f.df
    c, o = d["close"], d["open"]

    armed_short = _s(((c >= f.bb_up) & (f.rsi >= p.get("rsi_hi", 70.0))).shift(1)
                     .rolling(aw, min_periods=1).max().fillna(0).astype(bool))
    armed_long = _s(((c <= f.bb_dn) & (f.rsi <= p.get("rsi_lo", 30.0))).shift(1)
                    .rolling(aw, min_periods=1).max().fillna(0).astype(bool))
    short = armed_short & _s(c < o)
    long = armed_long & _s(c > o)
    return long, short, {"oscillator": _norm((f.rsi - 50).abs(), 10, 30)}


# --------------------------------------------------------------------------
# Mean-reversion expansion (2026-09-21). Regime attribution showed every trend
# family losing 27-106 points in recent2025_26 while the counter-trend family
# sat within noise of flat, so the tape is choppy and the search should widen
# here. These four are mechanisms the library did not have -- not new
# parameterisations of the RSI extreme (f_mean_reversion), the band touch
# (f_channel) or the 55-bar exhaustion turn (f_reversal).
# --------------------------------------------------------------------------

def f_failed_breakout(f: PairFeatures, p: dict):
    """The range high is taken out, then price closes back inside: a trap.

    Distinct from f_breakout_retest, which trades the CONTINUATION after a
    level holds, and from f_reversal, which needs an RSI extreme. This is
    purely structural -- no oscillator -- and fires against the break.
    """
    win = int(p.get("sweep_win", 4))
    lvl_h = f.hh20.shift(1)
    lvl_l = f.ll20.shift(1)
    d = f.df
    c, hi, lo = d["close"], d["high"], d["low"]
    poked_up = (hi > lvl_h).rolling(win, min_periods=1).max().fillna(0).astype(bool)
    poked_dn = (lo < lvl_l).rolling(win, min_periods=1).max().fillna(0).astype(bool)
    short = _s(poked_up & (c < lvl_h))     # failed upside break -> fade it
    long = _s(poked_dn & (c > lvl_l))      # failed downside break -> fade it
    depth = ((hi - lvl_h).abs() / f.atr.replace(0, np.nan)).fillna(0)
    return long, short, {"sweep": _norm(depth, 0.1, 1.5)}


def f_vwap_reversion(f: PairFeatures, p: dict):
    """Fade a stretch away from VWAP, measured in ATR.

    The engine carried vwap and vwap_dist as features and a vwap FILTER, but
    no family ever traded the distance itself.
    """
    k = float(p.get("stretch_atr", 2.0))
    long = _s(f.vwap_dist <= -k)
    short = _s(f.vwap_dist >= k)
    return long, short, {"vwap": _norm(f.vwap_dist.abs(), k, k * 2.5)}


def f_streak_exhaustion(f: PairFeatures, p: dict):
    """N consecutive closes in one direction, then fade the streak.

    Counting bars, with no band and no oscillator, is a different mechanism
    from every other counter-trend family here -- the Connors-style structural
    version of exhaustion.
    """
    n = int(p.get("streak", 4))
    c = f.df["close"]
    dn = (c < c.shift(1)).astype(int).rolling(n).sum() == n
    up = (c > c.shift(1)).astype(int).rolling(n).sum() == n
    return _s(dn), _s(up), {"streak": np.full(len(f.close), 0.65)}


def f_stretch_fade(f: PairFeatures, p: dict):
    """Fade an overextension from the slow EMA, measured in ATR.

    f_trendline_bounce uses the NEAR case (< 0.6 ATR from ema_slow); the far
    case was unused. Adapts to each pair's own volatility rather than a fixed
    percentage.
    """
    k = float(p.get("stretch_atr", 2.5))
    dist = ((f.df["close"] - f.ema_slow) / f.atr.replace(0, np.nan)).fillna(0)
    long = _s(dist <= -k)
    short = _s(dist >= k)
    return long, short, {"stretch": _norm(dist.abs(), k, k * 2.0)}


# --------------------------------------------------------------------------
# DEDICATED SHORT FAMILIES (2026-09-23).
#
# Every short leg in this library so far has been the mirror of a long entry,
# and the evidence says that is why shorts only pay in a sustained bear: the
# vb_b4 short leg loses -711.7 outright across 1811 trades and earns +820.8 in
# bear2022 alone. These nine are SHORT-ONLY BY CONSTRUCTION and encode things
# that are specific to downside moves rather than inverted upside logic:
#   * downside moves are faster and more violent, so conviction is read from
#     WHERE in the bar price closes, not just from the level being broken
#   * rallies into resistance fail differently from dips into support -- the
#     wick matters, because it is where trapped longs exit
#   * short squeezes punish strength, so strong-downtrend entries are avoided
#     in favour of stalling bounces
# Each returns an empty long mask, so direction can never smuggle a long in.
# --------------------------------------------------------------------------

def _no_long(n):
    return np.zeros(n, dtype=bool)


def f_breakdown(f: PairFeatures, p: dict):
    """Break of the N-bar low, closing in the lower part of the bar.

    A touch of the low is not a breakdown: the close has to finish near the
    bottom of its own range, which is what distinguishes supply from a wick.
    """
    n = len(f.close)
    d = f.df
    lo_lvl = f.ll20.shift(1)
    rng = (d["high"] - d["low"]).replace(0, np.nan)
    close_pos = (d["close"] - d["low"]) / rng          # 0 = closed on the low
    short = _s((d["close"] < lo_lvl) & (close_pos <= p.get("close_pos_max", 0.35)))
    return _no_long(n), short, {"breakdown": _norm(1 - close_pos.fillna(1), 0.5, 1.0)}


def f_resistance_rejection(f: PairFeatures, p: dict):
    """Rally into a swing high, rejected with an upper wick.

    Deliberately asymmetric to f_sr_rejection: the wick must be a real fraction
    of the bar, since that wick is where longs were filled and then trapped.
    """
    n = len(f.close)
    d = f.df
    k = p.get("tol_atr", 0.35)
    a = f.atr.replace(0, np.nan).to_numpy(float)
    at_res = np.abs(d["high"].to_numpy() - f.swing_h.to_numpy(float)) / a < k
    rng = (d["high"] - d["low"]).replace(0, np.nan)
    upper_wick = (d["high"] - np.maximum(d["close"], d["open"])) / rng
    short = _s(at_res & (upper_wick >= p.get("wick_min", 0.4)) & (d["close"] < d["open"]))
    return _no_long(n), short, {"rejection": _norm(upper_wick.fillna(0), 0.3, 0.7)}


def f_breakdown_retest(f: PairFeatures, p: dict):
    """Broke the low, came back to it, failed to reclaim it.

    The entry is the FAILURE to reclaim, not the break -- the level has to be
    proven as resistance from underneath.
    """
    n = len(f.close)
    d = f.df
    win = int(p.get("retest_win", 12))
    lvl = f.ll20.shift(1)
    broke = (d["close"] < lvl).rolling(win, min_periods=1).max().fillna(0).astype(bool)
    back_at = (d["high"] >= lvl) & (d["close"] < lvl)      # poked back up, rejected
    return _no_long(n), _s(broke.shift(1).fillna(False) & back_at),         {"retest": np.full(n, 0.7)}


def f_vwap_rejection(f: PairFeatures, p: dict):
    """Price rallies up to VWAP from below and turns down there."""
    n = len(f.close)
    d = f.df
    near = f.vwap_dist.abs() <= p.get("near_atr", 0.5)
    was_below = (f.vwap_dist < -p.get("near_atr", 0.5)).shift(1).rolling(
        int(p.get("win", 6)), min_periods=1).max().fillna(0).astype(bool)
    short = _s(near & was_below & (d["close"] < d["open"]))
    return _no_long(n), short, {"vwap": _norm(-f.vwap_dist, 0.0, 2.0)}


def f_lower_high(f: PairFeatures, p: dict):
    """Structure of successively lower highs -- short the confirmation."""
    n = len(f.close)
    d = f.df
    w = int(p.get("swing_win", 10))
    prior_high = d["high"].rolling(w).max().shift(w)
    this_high = d["high"].rolling(w).max()
    lower = this_high < prior_high
    short = _s(lower & (d["close"] < d["close"].shift(1)) & (d["close"] < d["open"]))
    return _no_long(n), short, {"structure": _norm(prior_high / this_high - 1, 0.0, 0.1)}


def f_bear_trend_continuation(f: PairFeatures, p: dict):
    """Established downtrend, short a bounce that STALLS.

    Not the mirror of trend continuation: it refuses to sell strength. Shorts
    taken into the strongest downtrends lost heavily to squeezes, so entry
    requires the bounce to fail rather than the trend to accelerate.
    """
    n = len(f.close)
    d = f.df
    dn = _s(f.ema_fast < f.ema_slow) & _s(d["close"] < f.ema_200)
    bounced = (d["close"] > d["close"].shift(1)).shift(1).rolling(
        int(p.get("bounce_win", 3)), min_periods=1).max().fillna(0).astype(bool)
    stalled = _s((d["close"] < d["open"]) & (d["close"] < f.ema_fast))
    not_extreme = _s(f.adx < p.get("adx_max", 35))       # avoid squeeze territory
    return _no_long(n), dn & _s(bounced) & stalled & not_extreme,         {"trend": _norm(f.adx, 15, 35)}


def f_bear_divergence(f: PairFeatures, p: dict):
    """Price makes a higher high while the oscillator does not."""
    n = len(f.close)
    short = _s(f.div_bear) & _s(f.df["close"] < f.df["open"])
    return _no_long(n), short, {"divergence": np.full(n, 0.75)}


def f_volume_breakdown(f: PairFeatures, p: dict):
    """Break of the low WITH volume expansion -- supply, not drift."""
    n = len(f.close)
    d = f.df
    lvl = f.ll20.shift(1)
    short = _s((d["close"] < lvl) & (f.vol_rel >= p.get("vol_mult", 1.5)))
    return _no_long(n), short, {"volume": _norm(f.vol_rel, 1.0, 3.0)}


def f_downside_vol_expansion(f: PairFeatures, p: dict):
    """Volatility expanding AND the move is down. Fires on one side only."""
    n = len(f.close)
    d = f.df
    expanding = _s(f.vol_expand >= p.get("expand_min", 1.3))
    down = _s((d["close"] < d["open"]) & (d["close"] < d["close"].shift(1)))
    return _no_long(n), expanding & down, {"expansion": _norm(f.vol_expand, 1.0, 2.0)}


FAMILIES = {
    "volatility_breakout": f_volatility_breakout,
    "breakout": f_breakout,
    "range_breakout": f_range_breakout,
    "trend_continuation": f_trend_continuation,
    "pullback": f_pullback,
    "mean_reversion": f_mean_reversion,
    "channel": f_channel,
    "sr_rejection": f_sr_rejection,
    "momentum": f_momentum,
    "vol_expansion": f_vol_expansion,
    "vol_contraction_break": f_vol_contraction_break,
    "trendline_bounce": f_trendline_bounce,
    "reentry_pullback": f_reentry_pullback,
    "reversal": f_reversal,
    "rsi_divergence": f_rsi_divergence,
    "breakout_retest": f_breakout_retest,
    # harvested from GreenAgent 2026-09-21
    "trend_resume": f_trend_resume,
    "rsi_reset": f_rsi_reset,
    "band_fade_confirmed": f_band_fade_confirmed,
    # mean-reversion expansion 2026-09-21
    "failed_breakout": f_failed_breakout,
    "vwap_reversion": f_vwap_reversion,
    "streak_exhaustion": f_streak_exhaustion,
    "stretch_fade": f_stretch_fade,
    # dedicated SHORT-ONLY families 2026-09-23
    "breakdown": f_breakdown,
    "resistance_rejection": f_resistance_rejection,
    "breakdown_retest": f_breakdown_retest,
    "vwap_rejection": f_vwap_rejection,
    "lower_high": f_lower_high,
    "bear_trend_continuation": f_bear_trend_continuation,
    "bear_divergence": f_bear_divergence,
    "volume_breakdown": f_volume_breakdown,
    "downside_vol_expansion": f_downside_vol_expansion,
}

# families that fight the prevailing trend by design
COUNTER_TREND = {"mean_reversion", "channel", "reversal", "rsi_divergence", "sr_rejection",
                 "band_fade_confirmed", "failed_breakout", "vwap_reversion",
                 "streak_exhaustion", "stretch_fade"}


# --------------------------------------------------------------------------
# Filter engine -- each filter is independently switchable and testable
# --------------------------------------------------------------------------

def filt_volume(f: PairFeatures, p: dict):
    return np.asarray(f.vol_rel >= p.get("vol_min", 1.0)), _norm(f.vol_rel, 0.8, 2.0)


def filt_not_flat(f: PairFeatures, p: dict):
    return ~np.asarray(f.regime["flat"]), _norm(f.vol_ratio, 0.6, 1.3)


def filt_trend_align(f: PairFeatures, p: dict):
    """Returns per-direction masks; handled specially by the builder."""
    up = np.asarray(f.close > f.ema_200)
    return up, _norm(f.adx, 15, 40)


def filt_volatility(f: PairFeatures, p: dict):
    lo, hi = p.get("vol_lo", 0.6), p.get("vol_hi", 2.5)
    ok = np.asarray((f.vol_ratio >= lo) & (f.vol_ratio <= hi))
    return ok, _norm(f.vol_ratio, 0.6, 1.6)


def filt_vol_expanding(f: PairFeatures, p: dict):
    return np.asarray(f.vol_expand > p.get("exp_min", 1.1)), _norm(f.vol_expand, 1.0, 1.8)


def filt_adx(f: PairFeatures, p: dict):
    return np.asarray(f.adx > p.get("adx_min", 20)), _norm(f.adx, 15, 40)


def filt_vwap(f: PairFeatures, p: dict):
    """Refuse entries stretched far from VWAP (poor risk/reward)."""
    return np.asarray(f.vwap_dist.abs() < p.get("vwap_max", 3.0)), \
        1 - _norm(f.vwap_dist.abs(), 0, 4)


def filt_btc_regime(f: PairFeatures, p: dict):
    """Market-wide directional gate, handled like trend_align."""
    if not hasattr(f, "_btcreg"):
        f._btcreg = btc_regime(len(f.close), f.date)
    return f._btcreg, np.full(len(f.close), 0.6)


FILTERS = {
    "btc_regime": filt_btc_regime,
    "volume": filt_volume,
    "not_flat": filt_not_flat,
    "trend_align": filt_trend_align,
    "volatility": filt_volatility,
    "vol_expanding": filt_vol_expanding,
    "adx": filt_adx,
    "vwap": filt_vwap,
}


def build_signals(f: PairFeatures, spec: dict):
    """Combine family triggers, filters and regime gate into scored signals.

    Returns (long_mask, short_mask, score_array, component_breakdown).
    """
    fam = spec["family"]
    p = spec.get("params", {})
    long, short, comp = FAMILIES[fam](f, p)

    n = len(f.close)
    scores = {k: np.asarray(v, dtype=float) for k, v in comp.items()}

    # ---- filters ----
    for name in spec.get("filters", []):
        fn = FILTERS[name]
        mask, sc = fn(f, p)
        scores[name] = np.asarray(sc, dtype=float)
        if name in ("trend_align", "btc_regime"):
            mode = spec.get("trend_mode", "with")
            if mode == "with":
                long = long & mask
                short = short & ~mask
            elif mode == "against":
                long = long & ~mask
                short = short & mask
            # "both" applies no directional constraint
        else:
            long = long & mask
            short = short & mask

    # ---- regime gate ----
    rg = spec.get("regime")
    if rg:
        r = f.regime
        gate = np.ones(n, dtype=bool)
        if "trend" in rg:
            gate &= np.asarray(r["trend"].isin(rg["trend"]))
        if "vol" in rg:
            gate &= np.asarray(r["vol"].isin(rg["vol"]))
        if "vol_state" in rg:
            gate &= np.asarray(r["vol_state"].isin(rg["vol_state"]))
        long, short = long & gate, short & gate

    # Short-side regime gate, separate from the long one. Measured on the dev
    # set: shorts opened in `strong_down` lost -623 while shorts opened in
    # `weak_down` made +200 -- the strongest-looking downtrends are where short
    # squeezes happen, so the short side gets its own allowed-state list.
    srg = spec.get("short_regime")
    if srg:
        short = short & np.asarray(f.regime["trend"].isin(srg))

    # ---- divergence penalty: a long into bearish divergence is suspect ----
    pen = np.zeros(n)
    pen[np.asarray(f.div_bear) & long] = spec.get("div_penalty", 0.15)
    pen[np.asarray(f.div_bull) & short] = spec.get("div_penalty", 0.15)
    scores["divergence_penalty"] = pen

    pos = [v for k, v in scores.items() if k != "divergence_penalty"]
    final = (np.mean(pos, axis=0) if pos else np.full(n, 0.5)) - pen
    final = np.clip(final, 0, 1)

    th = spec.get("min_score", 0.0)
    if th > 0:
        long = long & (final >= th)
        short = short & (final >= th)

    if spec.get("direction") == "long":
        short = np.zeros(n, dtype=bool)
    elif spec.get("direction") == "short":
        long = np.zeros(n, dtype=bool)

    return long, short, final, scores
