"""Opportunity engine - shared condition definitions.

The SAME code computes conditions on history (build_playbook.py) and on live
candles (scan.py), so a live alert means exactly what the casebook measured.

Input: hourly candles (date, open, high, low, close, volume) + funding
settlements (date, funding_rate). Only past data is used at every bar.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

COST_RT = 0.002            # fee 0.05% + slip 0.05% per side, both sides
HORIZONS = (8, 24, 48)     # hours a trade may stay open
MAXH = max(HORIZONS)
COOLDOWN = 48              # hours before the same condition can fire again on a coin

REGIMES = [
    ("bull2021", "2021-01-01", "2021-11-10"),
    ("bear2022", "2021-11-10", "2023-01-01"),
    ("recovery2023_24", "2023-01-01", "2025-01-01"),
    ("recent2025_26", "2025-01-01", "2026-10-01"),
]
FIT_END = "2025-01-01"     # rules are fitted before this date, tested after

# Plain-language description of each condition (shown in alerts).
CONDITIONS = {
    "FUND_HI":      "funding in top 5% of its last 90 days (longs paying a lot)",
    "FUND_LO":      "funding in bottom 5% of its last 90 days and negative (shorts paying)",
    "PUMP":         "24h move up >= 3x its normal daily move",
    "DUMP":         "24h move down >= 3x its normal daily move",
    "VOLSPIKE_UP":  "24h volume >= 3x its 30-day average, price up",
    "VOLSPIKE_DN":  "24h volume >= 3x its 30-day average, price down",
    "BRK_HI20":     "close above the 20-day high",
    "BRK_LO20":     "close below the 20-day low",
    "SQUEEZE":      "7-day volatility in lowest 5% of the last 180 days",
    "CROWD_LONG":   "funding top 5% while price rallied >= 1.5x normal (crowded longs)",
    "CROWD_SHORT":  "funding bottom 5% while price fell >= 1.5x normal (crowded shorts)",
    "FUND_DIV_DN":  "funding top 5% but price fell >= 1.5x normal",
    "FUND_DIV_UP":  "funding bottom 5% but price rose >= 1.5x normal",
}


def regular_grid(df: pd.DataFrame) -> pd.DataFrame:
    """Reindex to a complete hourly grid; missing bars = flat bar, 0 volume."""
    df = df[["date", "open", "high", "low", "close", "volume"]].copy()
    df["date"] = pd.to_datetime(df["date"], utc=True).dt.floor("h")
    df = df.drop_duplicates("date").set_index("date").sort_index()
    idx = pd.date_range(df.index[0], df.index[-1], freq="h", tz="UTC")
    df = df.reindex(idx)
    df["close"] = df["close"].ffill()
    for c in ("open", "high", "low"):
        df[c] = df[c].fillna(df["close"])
    df["volume"] = df["volume"].fillna(0.0).astype(float)
    df.index.name = "date"
    return df.reset_index()


def funding_features(df: pd.DataFrame, fund: pd.DataFrame | None) -> pd.DataFrame:
    """Per bar: last settled funding rate, its trailing 90-day percentile, and
    the funding a LONG pays during that bar (settlement inside the bar)."""
    out = pd.DataFrame({"date": df["date"]})
    if fund is None or fund.empty:
        out["frate"] = np.nan
        out["fpct"] = np.nan
        out["fpay"] = 0.0
        return out
    f = fund[["date", "funding_rate"]].copy()
    f["date"] = pd.to_datetime(f["date"], utc=True).dt.floor("h")
    f = f.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    f["fpct"] = f["funding_rate"].rolling(270, min_periods=90).rank(pct=True)
    m = pd.merge_asof(out, f.rename(columns={"funding_rate": "frate"}),
                      on="date", direction="backward")
    pay = f.set_index("date")["funding_rate"]
    m["fpay"] = pay.reindex(m["date"]).fillna(0.0).to_numpy()
    return m


def compute_conditions(df: pd.DataFrame, fund: pd.DataFrame | None) -> pd.DataFrame:
    """df must already be on a regular hourly grid (see regular_grid)."""
    x = df.copy()
    ff = funding_features(x, fund)
    x["frate"], x["fpct"], x["fpay"] = ff["frate"].to_numpy(), ff["fpct"].to_numpy(), ff["fpay"].to_numpy()

    lc = np.log(x["close"])
    r1 = lc.diff()
    sd = r1.rolling(720, min_periods=500).std()
    x["sigma24"] = sd * np.sqrt(24)                       # normal daily move (fraction)
    ret24 = lc - lc.shift(24)
    z24 = ret24 / x["sigma24"]
    vol24 = x["volume"].rolling(24).sum()
    volavg = x["volume"].rolling(720, min_periods=500).sum().shift(24) / 30.0
    vratio = vol24 / volavg.replace(0, np.nan)
    hi20 = x["high"].rolling(480, min_periods=480).max().shift(1)
    lo20 = x["low"].rolling(480, min_periods=480).min().shift(1)
    sd7 = r1.rolling(168, min_periods=150).std()
    sqz = sd7.rolling(4320, min_periods=2000).rank(pct=True)

    fhi = (x["fpct"] >= 0.95) & (x["frate"] > 0.0001)
    flo = (x["fpct"] <= 0.05) & (x["frate"] < 0)

    c = pd.DataFrame(index=x.index)
    c["FUND_HI"] = fhi
    c["FUND_LO"] = flo
    c["PUMP"] = z24 >= 3
    c["DUMP"] = z24 <= -3
    c["VOLSPIKE_UP"] = (vratio >= 3) & (ret24 > 0)
    c["VOLSPIKE_DN"] = (vratio >= 3) & (ret24 < 0)
    c["BRK_HI20"] = x["close"] > hi20
    c["BRK_LO20"] = x["close"] < lo20
    c["SQUEEZE"] = sqz <= 0.05
    c["CROWD_LONG"] = fhi & (z24 >= 1.5)
    c["CROWD_SHORT"] = flo & (z24 <= -1.5)
    c["FUND_DIV_DN"] = fhi & (z24 <= -1.5)
    c["FUND_DIV_UP"] = flo & (z24 >= 1.5)
    valid = x["sigma24"].notna() & (x["volume"] > 0)
    c = c.fillna(False).astype(bool) & valid.to_numpy()[:, None]

    x["z24"], x["vratio"] = z24, vratio
    return pd.concat([x, c], axis=1)


def triggers(cond: pd.Series) -> np.ndarray:
    """Bar indices where a condition switches on, with a per-coin cooldown."""
    on = cond.to_numpy() & ~np.r_[False, cond.to_numpy()[:-1]]
    idx, last = [], -10**9
    for i in np.flatnonzero(on):
        if i - last >= COOLDOWN:
            idx.append(i)
            last = i
    return np.asarray(idx, dtype=np.int64)


def paths(x: pd.DataFrame, idx: np.ndarray):
    """For each trigger bar i: entry at open of i+1, then MAXH bars of
    high/low/close relative to entry, and cumulative funding a long pays."""
    n = len(x)
    idx = idx[idx + 1 + MAXH <= n]
    if len(idx) == 0:
        return idx, None
    o, h, l, c, fp = (x[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close", "fpay"))
    entry = o[idx + 1]
    win = idx[:, None] + 1 + np.arange(MAXH)[None, :]
    P = {
        "entry": entry.astype(np.float64),
        "hi": (h[win] / entry[:, None] - 1).astype(np.float32),
        "lo": (l[win] / entry[:, None] - 1).astype(np.float32),
        "cl": (c[win] / entry[:, None] - 1).astype(np.float32),
        "fund": np.cumsum(fp[win], axis=1).astype(np.float32),
    }
    return idx, P


def simulate(P: dict, sigma: np.ndarray, d: int, H: int, tgt: float, stp: float):
    """Bracket per event. tgt/stp in sigma24 units. If target and stop are both
    touched in the same bar, the stop counts (conservative).
    Returns net return (fraction), outcome code (1 target, -1 stop, 0 time), exit bar."""
    hi, lo, cl, fu = P["hi"][:, :H], P["lo"][:, :H], P["cl"][:, :H], P["fund"][:, :H]
    fav = hi if d == 1 else -lo
    adv = -lo if d == 1 else hi
    T = (tgt * sigma)[:, None]
    S = (stp * sigma)[:, None]
    big = H + 1
    t_hit = np.where((fav >= T).any(1), (fav >= T).argmax(1), big)
    s_hit = np.where((adv >= S).any(1), (adv >= S).argmax(1), big)
    out = np.zeros(len(sigma), dtype=np.int8)
    gross = d * cl[:, -1].astype(float)
    ex = np.full(len(sigma), H - 1)
    stop_first = (s_hit <= t_hit) & (s_hit < big)
    tgt_first = (t_hit < s_hit)
    gross = np.where(stop_first, -S[:, 0], gross)
    gross = np.where(tgt_first, T[:, 0], gross)
    out[stop_first], out[tgt_first] = -1, 1
    ex = np.where(stop_first, s_hit, np.where(tgt_first, t_hit, ex))
    fund_paid = d * fu[np.arange(len(sigma)), ex]
    net = gross - COST_RT - fund_paid
    return net, out, ex
