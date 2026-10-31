r"""Protocol B panel: the 30 desk coins as 4-hour bars with positioning series.

    .venv\Scripts\python.exe -m quant.panel_pos        # -> data/panel_pos.npz

Prices from 15m klines; positioning from 5m metrics (last value in the bar; taker ratio = mean over the bar);
funding events summed into the bar that pays them. Zero open interest = missing.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from .panel import DEFAULT_MIN, Panel
from .paths import DATA, DESK, MIN_NOTIONAL

BAR = pd.Timedelta(hours=4)
START, END = pd.Timestamp("2024-09-01", tz="UTC"), pd.Timestamp("2026-09-26", tz="UTC")
FEATS = ["oi", "global_ls", "top_ls_positions", "top_ls_accounts", "taker_ls"]


def coins() -> list[str]:
    return sorted(d.name for d in DESK.iterdir() if d.is_dir() and (d / "metrics_5m.parquet").exists())


def build() -> Panel:
    grid = pd.date_range(START, END, freq=BAR, inclusive="left")
    mins = {r["pair"].split("/")[0]: max(x for x in (r["cost_min"], r["notional_filter"], 0) if x is not None)
            for r in json.loads(MIN_NOTIONAL.read_text(encoding="utf-8"))["rows"]}
    cols = {k: [] for k in ["close", "high", "low", "qvol", "fund"] + FEATS}
    names = []
    for sym in coins():
        k = pd.read_parquet(DESK / sym / "klines_15m.parquet", columns=["date", "high", "low", "close", "quote_volume"])
        k = k.set_index("date").sort_index()
        k = k[~k.index.duplicated()]
        g = k.resample(BAR, origin="epoch")
        b = pd.DataFrame({"close": g["close"].last(), "high": g["high"].max(), "low": g["low"].min(),
                          "qvol": g["quote_volume"].sum(min_count=1)})
        b.loc[g["close"].count() < 12, ["close", "high", "low"]] = np.nan
        b = b.reindex(grid)
        m = pd.read_parquet(DESK / sym / "metrics_5m.parquet")
        m["date"] = m["date"].dt.as_unit("ns")
        m = m.set_index("date").sort_index()
        m["oi"] = m["oi"].where(m["oi"] > 0)
        gm = m.resample(BAR, origin="epoch")
        feats = pd.DataFrame({f: gm[f].last() for f in FEATS if f != "taker_ls"})
        feats["taker_ls"] = gm["taker_ls"].mean()
        feats = feats.reindex(grid)
        f = pd.read_parquet(DESK / sym / "funding.parquet")
        t = f["date"].dt.floor("h").dt.as_unit("ns")
        kk = np.ceil(((t - grid[0]) / BAR).to_numpy(dtype=float)).astype(int) - 1
        ok = (kk >= 0) & (kk < len(grid))
        fund = np.bincount(kk[ok], weights=f["rate"].to_numpy()[ok], minlength=len(grid))
        names.append(sym[:-4])
        for c in ("close", "high", "low", "qvol"):
            cols[c].append(b[c].to_numpy(dtype=float))
        cols["fund"].append(fund)
        for c in FEATS:
            cols[c].append(feats[c].to_numpy(dtype=float))
    a = {c: np.column_stack(v) for c, v in cols.items()}
    return Panel(grid.as_unit("ns").asi8, names, a["close"], a["high"], a["low"], a["qvol"], a["fund"],
                 np.array([max(mins.get(c, DEFAULT_MIN), DEFAULT_MIN) for c in names]),
                 {c: a[c] for c in FEATS}, bars_per_day=6)


def save(p: Panel) -> None:
    np.savez_compressed(DATA / "panel_pos.npz", dates=p.dates, coins=np.array(p.coins), close=p.close,
                        high=p.high, low=p.low, qvol=p.qvol, fund=p.fund, min_notional=p.min_notional,
                        **{f"feat_{k}": v for k, v in p.feat.items()})


def load() -> Panel:
    z = np.load(DATA / "panel_pos.npz")
    return Panel(z["dates"], list(z["coins"]), z["close"], z["high"], z["low"], z["qvol"], z["fund"],
                 z["min_notional"], {k[5:]: z[k] for k in z.files if k.startswith("feat_")}, bars_per_day=6)


def main() -> int:
    p = build()
    save(p)
    print(f"{len(p.coins)} coins x {len(p.dates)} bars; features {list(p.feat)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
