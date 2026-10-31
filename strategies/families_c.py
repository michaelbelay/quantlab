"""Protocol C families (intraday, directional). Each returns (long_sig, short_sig, Exit) for one coin.

Signals are decided on the bar CLOSE using that bar and earlier bars only; trades.simulate enters at the
next bar's open. `ctx` carries bars_per_day (bpd), the timeframe, and BTC's close aligned to the coin.
Batch 1 registered 2026-10-05 (see FAMILIES_C.md) - one setting each, no grids.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quant.trades import Exit


def ema(x: pd.Series, n: int) -> pd.Series:
    return x.ewm(span=n, adjust=False).mean()


def rsi(c: pd.Series, n: int) -> pd.Series:
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def _b(x) -> np.ndarray:
    return np.nan_to_num(np.asarray(x, dtype=float), nan=0).astype(bool)


# C01 Donchian breakout: close beyond the prior 20-bar channel.
def c01_donchian(df, a, ctx):
    hi = df["high"].rolling(20).max().shift(1)
    lo = df["low"].rolling(20).min().shift(1)
    return _b(df["close"] > hi), _b(df["close"] < lo), Exit(2.0, 4.0, 2 * ctx["bpd"])


# C02 Squeeze breakout: Bollinger width in its lowest 20% of the last 100 bars, then a close outside the band.
def c02_squeeze(df, a, ctx):
    c = df["close"]
    m, s = c.rolling(20).mean(), c.rolling(20).std()
    width = (4 * s / m)
    tight = (width.rolling(100).rank(pct=True) <= 0.20).shift(1)
    return _b(tight & (c > m + 2 * s)), _b(tight & (c < m - 2 * s)), Exit(1.5, 3.0, ctx["bpd"])


# C03 EMA pullback in trend: EMA50 vs EMA200 trend; bar dips to EMA20 and closes back beyond it, in trend direction.
def c03_ema_pullback(df, a, ctx):
    c, o = df["close"], df["open"]
    e20, e50, e200 = ema(c, 20), ema(c, 50), ema(c, 200)
    up = (e50 > e200) & (df["low"] <= e20) & (c > e20) & (c > o)
    dn = (e50 < e200) & (df["high"] >= e20) & (c < e20) & (c < o)
    return _b(up), _b(dn), Exit(1.5, 3.0, 2 * ctx["bpd"])


# C04 RSI(2) reversion with the trend (Connors): oversold pullback in an uptrend / overbought in a downtrend.
def c04_rsi2(df, a, ctx):
    c = df["close"]
    r, e200 = rsi(c, 2), ema(c, 200)
    return _b((c > e200) & (r < 10)), _b((c < e200) & (r > 90)), Exit(2.0, 1.5, ctx["bpd"] // 2)


# C05 VWAP reversion: price more than 2.5 ATR from the rolling 1-day VWAP -> fade back.
def c05_vwap(df, a, ctx):
    n = ctx["bpd"]
    tp_ = (df["high"] + df["low"] + df["close"]) / 3
    vwap = (tp_ * df["volume"]).rolling(n).sum() / df["volume"].rolling(n).sum()
    dev = (df["close"] - vwap) / a
    return _b(dev < -2.5), _b(dev > 2.5), Exit(2.5, 1.5, ctx["bpd"])


# C06 Volume-confirmed breakout: 20-bar breakout on volume > 2x its 20-bar average.
def c06_volume_break(df, a, ctx):
    c, v = df["close"], df["volume"]
    loud = v > 2 * v.rolling(20).mean().shift(1)
    hi = df["high"].rolling(20).max().shift(1)
    lo = df["low"].rolling(20).min().shift(1)
    return _b(loud & (c > hi)), _b(loud & (c < lo)), Exit(2.0, 4.0, ctx["bpd"])


# C07 Delta divergence (15m/30m only, needs taker volume): price down over the last day while aggressive
# buying dominated (absorption) -> long; mirror -> short.
def c07_delta_div(df, a, ctx):
    if df["taker_buy"].isna().all():
        z = np.zeros(len(df), bool)
        return z, z, Exit()
    n = ctx["bpd"]
    delta = (2 * df["taker_buy"] - df["volume"]).rolling(n).sum()
    move = df["close"] / df["close"].shift(n) - 1
    vol_n = df["volume"].rolling(n).sum()
    share = delta / vol_n
    return _b((move < -2 * a / df["close"]) & (share > 0.05)), _b((move > 2 * a / df["close"]) & (share < -0.05)), \
        Exit(1.5, 3.0, ctx["bpd"] // 2)


# C08 Funding-extreme fade: last-24h funding far above its 30-day norm while price sits at a 3-day high -> short;
# mirror -> long.
def c08_funding_fade(df, a, ctx):
    n = ctx["bpd"]
    f24 = df["fund"].rolling(n).sum()
    z = (f24 - f24.rolling(30 * n).mean()) / f24.rolling(30 * n).std()
    c = df["close"]
    top = c >= c.rolling(3 * n).max()
    bot = c <= c.rolling(3 * n).min()
    return _b((z < -2) & bot), _b((z > 2) & top), Exit(2.0, 3.0, 2 * ctx["bpd"])


# C09 Relative strength vs BTC: coin beat BTC by > 2 ATR% over a day while BTC is above its 200-bar EMA -> long;
# lagged BTC by > 2 ATR% while BTC is below -> short.
def c09_rs_btc(df, a, ctx):
    n = ctx["bpd"]
    b = ctx["btc"]
    if b is None:
        z = np.zeros(len(df), bool)
        return z, z, Exit()
    rel = (df["close"] / df["close"].shift(n)) - (b / b.shift(n))
    thr = 2 * a / df["close"]
    btc_up = b > ema(b, 200)
    return _b((rel > thr) & btc_up), _b((rel < -thr) & ~btc_up & b.notna()), Exit(2.0, 4.0, 2 * ctx["bpd"])


# C10 Session breakout: the 00:00-08:00 UTC range; first close above/below it later the same day.
def c10_session(df, a, ctx):
    d = df["date"]
    day = d.dt.floor("D")
    asia = d.dt.hour < 8
    rh = df["high"].where(asia).groupby(day).transform("max")
    rl = df["low"].where(asia).groupby(day).transform("min")
    after = ~asia & (d.dt.hour < 20)
    up = after & (df["close"] > rh)
    dn = after & (df["close"] < rl)
    first_up = up & ~up.groupby(day).shift(1, fill_value=False).groupby(day).cummax()
    first_dn = dn & ~dn.groupby(day).shift(1, fill_value=False).groupby(day).cummax()
    return _b(first_up), _b(first_dn), Exit(1.5, 3.0, ctx["bpd"] * 2 // 3)


BATCH1 = {"C01": c01_donchian, "C02": c02_squeeze, "C03": c03_ema_pullback, "C04": c04_rsi2, "C05": c05_vwap,
          "C06": c06_volume_break, "C07": c07_delta_div, "C08": c08_funding_fade, "C09": c09_rs_btc,
          "C10": c10_session}


# ------------------------------------------------------------------ batch 2 (registered 2026-10-05)
def _short_only(fn, hedge: bool = False):
    def f(df, a, ctx):
        ls, ss, ex = fn(df, a, ctx)
        return np.zeros_like(ls), ss, ex
    f.hedge = hedge
    return f


BATCH2 = {"C11": _short_only(c01_donchian), "C12": _short_only(c06_volume_break), "C13": _short_only(c10_session),
          "C14": _short_only(c08_funding_fade),
          "C15": _short_only(c01_donchian, True), "C16": _short_only(c06_volume_break, True),
          "C17": _short_only(c10_session, True), "C18": _short_only(c08_funding_fade, True)}


# ------------------------------------------------------------------ batch 3 (registered 2026-10-05)
def c19_funding_stall(df, a, ctx):
    _, ss, ex = c08_funding_fade(df, a, ctx)
    stall = df["close"] < df["low"].shift(1)
    return np.zeros_like(ss), ss & _b(stall), ex


def c20_funding_long_unwind(df, a, ctx):
    _, ss, _ = c08_funding_fade(df, a, ctx)
    return np.zeros_like(ss), ss, Exit(2.0, 5.0, 4 * ctx["bpd"])


def _spike(df, ctx):
    n = ctx["bpd"]
    r24 = df["close"] / df["close"].shift(n) - 1
    v24 = df["volume"].rolling(n).sum()
    v7 = df["volume"].rolling(7 * n).sum() / 7
    return r24, v24 > 2 * v7.shift(n)


def c24_pump_fade(df, a, ctx):
    r24, loud = _spike(df, ctx)
    s = _b((r24 >= 0.15) & loud)
    return np.zeros_like(s), s, Exit(3.0, 4.0, 2 * ctx["bpd"])


def c25_capitulation(df, a, ctx):
    r24, loud = _spike(df, ctx)
    f24 = df["fund"].rolling(ctx["bpd"]).sum()
    l_ = _b((r24 <= -0.15) & loud & (f24 < 0))
    return l_, np.zeros_like(l_), Exit(3.0, 4.0, 2 * ctx["bpd"])


def c26_spike_both(df, a, ctx):
    l_, _, ex = c25_capitulation(df, a, ctx)
    _, s, _ = c24_pump_fade(df, a, ctx)
    return l_, s, ex


BATCH3 = {"C19": c19_funding_stall, "C20": c20_funding_long_unwind, "C24": c24_pump_fade,
          "C25": c25_capitulation, "C26": c26_spike_both}


# ------------------------------------------------------------------ batch 4 (registered 2026-10-05)
LIQ_TOP = 40


def _liquid(ctx, n):
    r = ctx.get("liq_rank")
    return np.zeros(n, bool) if r is None else np.nan_to_num(r, nan=1e9) <= LIQ_TOP


def c27_capitulation_liquid(df, a, ctx):
    l_, s_, ex = c25_capitulation(df, a, ctx)
    return l_ & _liquid(ctx, len(df)), s_, ex


def c28_crowded_pump_fade(df, a, ctx):
    r24, loud = _spike(df, ctx)
    n = ctx["bpd"]
    f24 = df["fund"].rolling(n).sum()
    fz = (f24 - f24.rolling(30 * n).mean()) / f24.rolling(30 * n).std()
    s = _b((r24 >= 0.15) & loud & (f24 > 0) & (fz > 1)) & _liquid(ctx, len(df))
    return np.zeros_like(s), s, Exit(3.0, 4.0, 2 * ctx["bpd"])


def c29_crowding_both(df, a, ctx):
    l_, _, ex = c27_capitulation_liquid(df, a, ctx)
    _, s, _ = c28_crowded_pump_fade(df, a, ctx)
    return l_, s, ex


def c30_crowding_hedged(df, a, ctx):
    return c29_crowding_both(df, a, ctx)


c30_crowding_hedged.hedge = True
BATCH4 = {"C27": c27_capitulation_liquid, "C28": c28_crowded_pump_fade, "C29": c29_crowding_both,
          "C30": c30_crowding_hedged}


# ------------------------------------------------------------------ batch 5 (registered 2026-10-05)
def c31_funding_liquid(df, a, ctx):
    l_, s, ex = c14_like(df, a, ctx)
    return l_, s & _liquid(ctx, len(df)), ex


def c14_like(df, a, ctx, z_thr: float = 2.0):
    n = ctx["bpd"]
    f24 = df["fund"].rolling(n).sum()
    z = (f24 - f24.rolling(30 * n).mean()) / f24.rolling(30 * n).std()
    top = df["close"] >= df["close"].rolling(3 * n).max()
    s = _b((z > z_thr) & top)
    return np.zeros_like(s), s, Exit(2.0, 3.0, 2 * ctx["bpd"])


def c32_funding_extreme(df, a, ctx):
    return c14_like(df, a, ctx, 2.5)


def c34_funding_long_regime(df, a, ctx):
    n = ctx["bpd"]
    f24 = df["fund"].rolling(n).sum()
    z = (f24 - f24.rolling(30 * n).mean()) / f24.rolling(30 * n).std()
    bot = df["close"] <= df["close"].rolling(3 * n).min()
    b = ctx["btc"]
    if b is None:
        z0 = np.zeros(len(df), bool)
        return z0, z0, Exit()
    up = _b(b > ema(b, 200))
    l_ = _b((z < -2) & bot) & up
    return l_, np.zeros_like(l_), Exit(2.0, 3.0, 2 * ctx["bpd"])


def _settlement(df, ctx, sign: int):
    if ctx["tf"] != "1h":
        z0 = np.zeros(len(df), bool)
        return z0
    ev = df["fund"].where(df["fund"] != 0)
    last_rate = ev.ffill()                                    # most recent settled rate, known at the bar close
    hour = df["date"].dt.hour
    pre = hour.isin([4, 12, 20])                               # bar 04:00-05:00 closes at 05:00 = 3h before 08:00
    cond = (last_rate >= 0.0005) if sign < 0 else (last_rate <= -0.0005)
    return _b(pre & cond)


def c36_settle_short(df, a, ctx):
    s = _settlement(df, ctx, -1)
    return np.zeros_like(s), s, Exit(2.0, None, 4)


def c37_settle_long(df, a, ctx):
    l_ = _settlement(df, ctx, +1)
    return l_, np.zeros_like(l_), Exit(2.0, None, 4)


def c38_settle_both(df, a, ctx):
    return _settlement(df, ctx, +1), _settlement(df, ctx, -1), Exit(2.0, None, 4)


BATCH5 = {"C31": c31_funding_liquid, "C32": c32_funding_extreme, "C34": c34_funding_long_regime,
          "C36": c36_settle_short, "C37": c37_settle_long, "C38": c38_settle_both}


# ------------------------------------------------------------------ batch 6 (registered 2026-10-13)
def c41_momentum_sr(df, a, ctx):
    """Momentum break of support/resistance on the 15m (Michael's snipe idea, FAMILIES_C.md batch 6).

    Level: the most recent CONFIRMED swing high (resistance) / swing low (support) - a bar whose high/low is
    above/below the 2 bars before AND after it; the level becomes usable 2 bars after it forms, so no lookahead.
    Momentum: the signal bar closes beyond the level AND its range (high-low) is >= 1.5x the prior 20-bar
    average range (a real impulse candle, not a drift-through). Exit: tight snipe (1.5 ATR stop, 3 ATR target,
    8-bar / 2-hour cap). Both directions.
    """
    h, l, c = df["high"], df["low"], df["close"]
    sh = (h > h.shift(1)) & (h > h.shift(2)) & (h > h.shift(-1)) & (h > h.shift(-2))
    sl = (l < l.shift(1)) & (l < l.shift(2)) & (l < l.shift(-1)) & (l < l.shift(-2))
    res = h.where(sh).ffill().shift(2)          # last confirmed swing high, known at the signal bar's close
    sup = l.where(sl).ffill().shift(2)          # last confirmed swing low
    rng = h - l
    impulse = rng >= 1.5 * rng.rolling(20).mean().shift(1)
    return _b(impulse & (c > res)), _b(impulse & (c < sup)), Exit(1.5, 3.0, 8)


BATCH6 = {"C41": c41_momentum_sr}
