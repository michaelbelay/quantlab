r"""8-hour bar panels (time x coin) built from 1h futures candles + real funding history.

    .venv\\Scripts\\python.exe -m quant.panel          # builds data/panel_dev.npz and data/panel_oos.npz

Bars are [t, t+8h) at 00/08/16 UTC. `fund[i]` is the summed funding rate of every funding event in
(bar_open, bar_close] - i.e. what a position held through bar i pays (longs pay positive rates).
Loaded one coin at a time: the host has little free memory.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .paths import DATA, FUT, MIN_NOTIONAL, OOS, dev_coins, oos_coins

BAR = pd.Timedelta(hours=8)
START = pd.Timestamp("2021-01-01", tz="UTC")
END = pd.Timestamp("2026-09-26", tz="UTC")      # last bar opens 2026-09-25 16:00
DEFAULT_MIN = 5.0


@dataclass
class Panel:
    dates: np.ndarray          # bar open times, datetime64[ns, UTC] as int64 ns
    coins: list[str]
    close: np.ndarray          # [T, N] float64, NaN where the coin has no data
    high: np.ndarray
    low: np.ndarray
    qvol: np.ndarray           # quote volume (USDT) in the bar
    fund: np.ndarray           # summed funding rate charged at the end of the bar (0 if none)
    min_notional: np.ndarray   # [N] USDT
    feat: dict | None = None   # optional extra [T, N] series (Protocol B positioning data)
    bars_per_day: int = 3

    @property
    def index(self) -> pd.DatetimeIndex:
        return pd.to_datetime(self.dates, utc=True)

    def window(self, start: str, end: str) -> "Panel":
        idx = self.index
        m = (idx >= pd.Timestamp(start, tz="UTC")) & (idx < pd.Timestamp(end, tz="UTC"))
        return Panel(self.dates[m], self.coins, self.close[m], self.high[m], self.low[m],
                     self.qvol[m], self.fund[m], self.min_notional,
                     {k: v[m] for k, v in self.feat.items()} if self.feat else None, self.bars_per_day)

    def subset(self, coins: list[str]) -> "Panel":
        j = [self.coins.index(c) for c in coins]
        return Panel(self.dates, [self.coins[i] for i in j], self.close[:, j], self.high[:, j], self.low[:, j],
                     self.qvol[:, j], self.fund[:, j], self.min_notional[j])


def _bars(h: pd.DataFrame, f: pd.DataFrame | None, grid: pd.DatetimeIndex) -> pd.DataFrame:
    h = h.set_index("date").sort_index()
    h = h[~h.index.duplicated()]
    g = h.resample(BAR, origin="epoch", label="left", closed="left")
    b = pd.DataFrame({"close": g["close"].last(), "high": g["high"].max(), "low": g["low"].min(),
                      "qvol": (h["close"] * h["volume"]).resample(BAR, origin="epoch").sum(min_count=1)})
    n = g["close"].count()
    b.loc[n < 6, ["close", "high", "low"]] = np.nan         # a bar needs most of its 8 candles
    b = b.reindex(grid)
    b["fund"] = 0.0
    if f is not None and len(f):
        t = f["date"].dt.floor("h")
        rate = f.iloc[:, 1].astype(float).to_numpy()
        # event at time e is paid by the bar whose (open, close] contains e
        k = np.ceil(((t - grid[0]) / BAR).to_numpy(dtype=float)).astype(int) - 1
        ok = (k >= 0) & (k < len(grid))
        b["fund"] = np.bincount(k[ok], weights=rate[ok], minlength=len(grid))
    return b


def build(kind: str) -> Panel:
    coins = dev_coins() if kind == "dev" else oos_coins()
    grid = pd.date_range(START, END, freq=BAR, inclusive="left")
    mins = {r["pair"].split("/")[0]: max(x for x in (r["cost_min"], r["notional_filter"], 0) if x is not None)
            for r in json.loads(MIN_NOTIONAL.read_text(encoding="utf-8"))["rows"]}
    cols = {k: [] for k in ("close", "high", "low", "qvol", "fund")}
    kept = []
    for i, c in enumerate(coins, 1):
        if kind == "dev":
            h = pd.read_feather(FUT / f"{c}_USDT_USDT-1h-futures.feather")
            fp = FUT / f"{c}_USDT_USDT-1h-funding_rate.feather"
        else:
            h = pd.read_feather(OOS / f"{c}USDT" / "ohlcv_1h.feather")
            fp = OOS / f"{c}USDT" / "funding.feather"
        f = pd.read_feather(fp) if fp.exists() else None
        b = _bars(h, f, grid)
        if b["close"].notna().sum() < 90:
            continue
        kept.append(c)
        for k in cols:
            cols[k].append(b[k].to_numpy(dtype=np.float64))
        if i % 50 == 0:
            print(f"  {kind}: {i}/{len(coins)}", flush=True)
    arr = {k: np.column_stack(v) for k, v in cols.items()}
    return Panel(grid.as_unit("ns").asi8, kept, arr["close"], arr["high"], arr["low"], arr["qvol"], arr["fund"],
                 np.array([max(mins.get(c, DEFAULT_MIN), DEFAULT_MIN) for c in kept]))


def save(p: Panel, kind: str) -> None:
    np.savez_compressed(DATA / f"panel_{kind}.npz", dates=p.dates, coins=np.array(p.coins), close=p.close,
                        high=p.high, low=p.low, qvol=p.qvol, fund=p.fund, min_notional=p.min_notional)


def load(kind: str) -> Panel:
    z = np.load(DATA / f"panel_{kind}.npz")
    return Panel(z["dates"], list(z["coins"]), z["close"], z["high"], z["low"], z["qvol"], z["fund"],
                 z["min_notional"])


def main() -> int:
    DATA.mkdir(exist_ok=True)
    for kind in ("dev", "oos"):
        p = build(kind)
        save(p, kind)
        print(f"{kind}: {len(p.coins)} coins x {len(p.dates)} bars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
