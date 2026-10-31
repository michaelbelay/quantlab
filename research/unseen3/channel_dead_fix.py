"""Correction of the channel row in UNSEEN3_RESULT_2026-10-09.md: remove phantom trades on frozen-price coins.

Same trades (trades_channel_uphivol.parquet, written by the frozen unseen3.py run), same pass rule (unseen3.PASS),
same summary function (incubator.summarize). The ONLY change: a trade is dropped when its coin was not trading at
the signal bar, by the DEAD rule of cap300/channel_redesign.py (fixed before this run):
    entry bar (signal bar + 1) has high == low, OR 12+ of the 24 bars up to the signal bar have high == low,
    OR atr_pct at the signal bar < 0.0001.
This is a data correction, not a new look: no idea, rule or parameter changes. Random baseline is not recomputed
(the channel is an engine idea; unseen3 had none for it either).

    .venv\\Scripts\\python.exe research\\unseen3\\channel_dead_fix.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / "research"), str(ROOT / "research" / "engine"), str(ROOT / "research" / "incubator"),
                str(HERE)]
import downtrend as D  # noqa: E402
import incubator as I  # noqa: E402
from unseen3 import PASS, daily  # noqa: E402


def dead_flags(tr: pd.DataFrame) -> np.ndarray:
    R = I.load_idea(ROOT / "research" / "pipeline" / "run.py")
    files = {c: (p, fp) for c, p, fp in D.oos_files()}
    dead = np.zeros(len(tr), bool)
    for coin, idx in tr.groupby("coin").groups.items():
        f = R.load(*files[coin])
        dates = pd.DatetimeIndex(pd.to_datetime(f.date, utc=True))
        flat = f.high == f.low
        flat24 = pd.Series(flat.astype(int)).rolling(24, min_periods=1).sum().to_numpy()
        atrp = f.atr_pct.to_numpy(float)
        pos = dates.get_indexer(pd.DatetimeIndex(tr.loc[idx, "date"]))
        assert (pos >= 0).all() and (pos + 1 < len(flat)).all(), coin
        dead[tr.index.get_indexer(idx)] = flat[pos + 1] | (flat24[pos] >= 12) | (atrp[pos] < 1e-4)
    return dead


def verdict(tr: pd.DataFrame) -> dict:
    s = I.summarize(tr)
    dd = daily(tr)
    s["day_avg_without_top3"] = float(dd.sort_values(ascending=False).iloc[PASS["drop_top_days"]:].mean())
    # evidence check reported in UNSEEN3 (not part of the pass rule): weekly / monthly t
    for name, rule in (("weekly_t", "W"), ("monthly_t", "MS")):
        g = dd.groupby(dd.index.to_period(rule[0])).mean()
        s[name] = float(g.mean() / g.std(ddof=1) * np.sqrt(len(g))) if len(g) > 2 else None
        s[name.replace("_t", "_n")] = int(len(g))
    s["passed"] = bool(s["trades"] >= PASS["min_trades"] and s["day_avg_pct"] > 0
                       and (s["day_t"] or 0) >= PASS["min_t"] and (s["pf_2x"] or 0) >= PASS["min_pf_2x"]
                       and s["day_avg_without_top3"] > 0)
    return s


def main():
    tr = pd.read_parquet(HERE / "trades_channel_uphivol.parquet").reset_index(drop=True)
    tr["dead"] = dead_flags(tr)
    out = {"rule": "DEAD filter of cap300/channel_redesign.py", "pass_rule": PASS,
           "dead_trades": int(tr.dead.sum()), "dead_mean_pnl": float(tr[tr.dead].pnl.mean()),
           "dead_coins": sorted(tr[tr.dead].coin.unique().tolist()),
           "before": verdict(tr), "after": verdict(tr[~tr.dead].reset_index(drop=True))}
    (HERE / "channel_dead_fix.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    keys = ("trades", "days", "pf", "pf_2x", "day_avg_pct", "day_t", "day_avg_without_top3", "weekly_t",
            "monthly_t", "passed")
    print(f"dead trades {out['dead_trades']} (mean {out['dead_mean_pnl']:+.3f}%) on {len(out['dead_coins'])} coins")
    for k in ("before", "after"):
        print(k, json.dumps({x: out[k].get(x) for x in keys}, default=str))
    print("years after:", {y: round(v["net"]) for y, v in out["after"]["years"].items()})


if __name__ == "__main__":
    main()
