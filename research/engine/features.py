"""Data loading, indicator precomputation and the market-regime engine.

Everything a strategy might need is computed ONCE per (pair, timeframe) and
cached. A generated strategy is then just boolean algebra over these arrays,
which is what makes a tournament of hundreds of candidates affordable -- the
old bot-backtest subprocess path costs ~6 minutes per backtest, this costs
milliseconds per strategy.
"""
from __future__ import annotations

import functools
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FUT = ROOT / "data" / "market" / "dev_1h" / "binance" / "futures"
SPOT = ROOT / "data" / "market" / "dev_1h" / "binance"

# coin sets kept deliberately separate: B is never used to choose anything
DEV_COINS = ["BTC", "ETH", "SOL", "XRP", "LINK", "LTC", "ADA", "AVAX"]
HOLDOUT_COINS = ["DOGE", "DOT", "ATOM", "UNI", "BCH", "ETC", "TRX", "NEAR"]


def _rma(x: pd.Series, n: int) -> pd.Series:
    """Wilder's smoothing, as used by ATR/ADX/RSI."""
    return x.ewm(alpha=1 / n, adjust=False).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = _rma(d.clip(lower=0), n)
    dn = _rma((-d).clip(lower=0), n)
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return _rma(tr, n)


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    up = df["high"].diff()
    dn = -df["low"].diff()
    plus = np.where((up > dn) & (up > 0), up, 0.0)
    minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    a = atr(df, n).replace(0, np.nan)
    pdi = 100 * _rma(pd.Series(plus, index=df.index), n) / a
    mdi = 100 * _rma(pd.Series(minus, index=df.index), n) / a
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return _rma(dx, n).fillna(0)


def swing_levels(df: pd.DataFrame, left: int = 3, right: int = 3):
    """Confirmed swing highs/lows.

    A swing is only confirmed `right` bars after it forms, so the value is
    shifted forward by `right` -- without that shift the level would be known
    before it existed, which is lookahead.
    """
    h, l = df["high"], df["low"]
    is_h = (h == h.rolling(left + right + 1, center=True).max())
    is_l = (l == l.rolling(left + right + 1, center=True).min())
    sh = h.where(is_h).shift(right).ffill()
    sl = l.where(is_l).shift(right).ffill()
    return sh, sl


class PairFeatures:
    """All precomputed arrays for one pair/timeframe."""

    def __init__(self, df: pd.DataFrame, funding: pd.DataFrame | None = None):
        self.df = df.reset_index(drop=True)
        d = self.df
        c, h, l, v = d["close"], d["high"], d["low"], d["volume"]

        self.date = d["date"].values
        self.open = d["open"].to_numpy(float)
        self.high = h.to_numpy(float)
        self.low = l.to_numpy(float)
        self.close = c.to_numpy(float)

        # --- volatility -----------------------------------------------------
        self.atr = atr(d, 14)
        self.atr_pct = (self.atr / c).fillna(0)
        self.atr_med = self.atr_pct.rolling(200).median()
        self.vol_ratio = (self.atr_pct / self.atr_med).fillna(1.0)
        # expansion/contraction: short ATR vs long ATR
        self.atr_fast = atr(d, 5)
        self.vol_expand = (self.atr_fast / self.atr.replace(0, np.nan)).fillna(1.0)

        # --- trend ----------------------------------------------------------
        self.ema_fast = c.ewm(span=21, adjust=False).mean()
        self.ema_slow = c.ewm(span=55, adjust=False).mean()
        self.ema_200 = c.ewm(span=200, adjust=False).mean()
        self.adx = adx(d, 14)
        self.slope = (self.ema_fast - self.ema_fast.shift(10)) / self.atr.replace(0, np.nan)

        # --- momentum -------------------------------------------------------
        self.rsi = rsi(c, 14)
        self.rsi_slow = rsi(c, 28)
        self.mom = (c / c.shift(20) - 1).fillna(0)

        # --- volume ---------------------------------------------------------
        vmed = v.rolling(100).median().replace(0, np.nan)
        self.vol_rel = (v / vmed).fillna(1.0)          # normalised, not a fixed threshold
        self.vol_trend = (v.rolling(5).mean() / v.rolling(50).mean().replace(0, np.nan)).fillna(1.0)

        # --- structure / levels ---------------------------------------------
        for n in (20, 55):
            setattr(self, f"hh{n}", h.rolling(n).max().shift(1))
            setattr(self, f"ll{n}", l.rolling(n).min().shift(1))
        self.range_w = ((self.hh20 - self.ll20) / c).fillna(0)
        self.swing_h, self.swing_l = swing_levels(d)

        # Bollinger + squeeze (volatility contraction)
        ma = c.rolling(20).mean()
        sd = c.rolling(20).std()
        self.bb_up, self.bb_dn, self.bb_mid = ma + 2 * sd, ma - 2 * sd, ma
        self.bb_width = ((self.bb_up - self.bb_dn) / ma.replace(0, np.nan)).fillna(0)
        self.squeeze = (self.bb_width / self.bb_width.rolling(100).median().replace(0, np.nan)).fillna(1.0)

        # rolling VWAP proxy (typical price weighted), 100-bar
        tp = (h + l + c) / 3
        self.vwap = ((tp * v).rolling(100).sum() / v.rolling(100).sum().replace(0, np.nan)).ffill()
        self.vwap_dist = ((c - self.vwap) / self.atr.replace(0, np.nan)).fillna(0)

        # trend-line proxy: linear regression slope over 50 bars, in ATR units
        self.tl_slope = (self.ema_slow - self.ema_slow.shift(50)) / self.atr.replace(0, np.nan)

        # RSI divergence over a 30-bar window, confirmed (shifted) to avoid lookahead
        self.div_bull, self.div_bear = self._divergence(c, self.rsi, 30)

        # funding cost per bar (futures); 8h funding spread across bars
        self.funding = np.zeros(len(d))
        if funding is not None and not funding.empty:
            f = funding.set_index("date")["funding_rate"]
            aligned = f.reindex(d["date"], method="ffill").fillna(0).to_numpy(float)
            self.funding = aligned / 8.0   # 1h bars, funding charged per 8h

        self.regime = self._classify()

    @staticmethod
    def _divergence(close: pd.Series, r: pd.Series, win: int):
        """Price makes a new extreme, RSI does not -- classic divergence."""
        pl = close.rolling(win).min()
        rl = r.rolling(win).min()
        bull = (close <= pl) & (r > rl * 1.05)
        ph = close.rolling(win).max()
        rh = r.rolling(win).max()
        bear = (close >= ph) & (r < rh * 0.95)
        return (bull.shift(1).fillna(False).astype(bool),
                bear.shift(1).fillna(False).astype(bool))

    def _classify(self) -> pd.DataFrame:
        """Machine-readable regime state per bar."""
        up = self.ema_fast > self.ema_slow
        above = self.close > self.ema_200.to_numpy()
        strong = self.adx > 25
        trend = pd.Series("range", index=self.df.index, dtype=object)
        trend[up & above & strong] = "strong_up"
        trend[up & above & ~strong] = "weak_up"
        trend[~up & ~above & strong] = "strong_down"
        trend[~up & ~above & ~strong] = "weak_down"

        vol = pd.Series("normal", index=self.df.index, dtype=object)
        vol[self.vol_ratio < 0.7] = "low"
        vol[self.vol_ratio > 1.4] = "high"

        vstate = pd.Series("stable", index=self.df.index, dtype=object)
        vstate[self.vol_expand > 1.25] = "expanding"
        vstate[self.vol_expand < 0.8] = "contracting"

        flat = (self.vol_ratio < 0.7) & (self.adx < 20)
        return pd.DataFrame({
            "trend": trend, "vol": vol, "vol_state": vstate,
            "flat": flat, "squeeze": self.squeeze < 0.7,
            "vol_expanding_now": self.vol_expand > 1.25,
            "bull": pd.Series(above, index=self.df.index),
            "adx": self.adx,
        })


@functools.lru_cache(maxsize=64)
def load_pair(coin: str, tf: str = "1h", futures: bool = True) -> PairFeatures | None:
    if futures:
        p = FUT / f"{coin}_USDT_USDT-{tf}-futures.feather"
        fp = FUT / f"{coin}_USDT_USDT-{tf}-funding_rate.feather"
        if not fp.exists():
            fp = FUT / f"{coin}_USDT_USDT-1h-funding_rate.feather"
    else:
        p = SPOT / f"{coin}_USDT-{tf}.feather"
        fp = None
    if not p.exists():
        return None
    df = pd.read_feather(p)
    fund = pd.read_feather(fp) if fp is not None and fp.exists() else None
    return PairFeatures(df, fund)


def load_universe(coins: list[str], tf: str = "1h", futures: bool = True) -> dict[str, PairFeatures]:
    out = {}
    for c in coins:
        f = load_pair(c, tf, futures)
        if f is not None:
            out[c] = f
    return out
