"""Unseen-coin test of 3 incubator ideas (pre-registered: research/PREREGISTRATION_2026-10-09_unseen3.md).

Run ONCE:  .venv\\Scripts\\python.exe research\\unseen3\\unseen3.py
Writes research/unseen3/result.json and per-idea trade parquets. Refuses to run if a frozen file changed.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / "research"), str(ROOT / "research" / "incubator")]
import downtrend as D  # noqa: E402
import incubator as I  # noqa: E402
from regime_switch import market_types  # noqa: E402

A, B = "2021-01-01", "2026-09-25"
IDEAS = ["research/incubator/ideas/flush_f1.py", "research/incubator/ideas/absorption_up.py",
         "research/incubator/ideas/channel_uphivol.py"]
PASS = {"min_trades": 100, "min_t": 2.4, "min_pf_2x": 1.0, "drop_top_days": 3}
REPS, SEED = 200, 20261009


def check_hashes():
    bad = []
    for line in (HERE / "hashes.txt").read_text(encoding="utf-8").splitlines():
        h, f = line.split(maxsplit=1)
        if hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != h:
            bad.append(f)
    if bad:
        raise SystemExit(f"frozen files changed: {bad}")


def daily(tr):
    return (tr.pnl * tr.w).groupby(tr.day).sum() / tr.w.groupby(tr.day).sum()


def random_pct(U, tr, m):
    """Same number of trades per entry day, random coins/hours of that day, same side/hold/stop; no market filter
    needed because the entry days are the idea's own days."""
    rng = np.random.default_rng(SEED)
    okidx = np.flatnonzero(U.ok & np.r_[U.ok[1:], False])
    by_day = pd.Series(okidx, index=pd.DatetimeIndex(U.date.iloc[okidx].dt.floor("D"))).groupby(level=0).apply(np.array)
    cnt = tr.groupby("day").size()
    sig = U.g.sigma.to_numpy(float)
    real = daily(tr).mean()
    tot = np.zeros(REPS)
    for r in range(REPS):
        picks = [rng.choice(by_day[d], size=n) for d, n in cnt.items() if d in by_day.index]
        s = np.concatenate(picks)
        rt = D.simulate(U, s + 1, m.SIDE, np.full(len(s), m.HOLD), m.STOP_K, sig[s])
        rt["day"] = pd.to_datetime(U.date.iloc[rt.ent.to_numpy()].to_numpy(), utc=True).floor("D")
        tot[r] = rt.pnl.groupby(rt.day).mean().mean()
    return float((tot < real).mean() * 100), float(np.median(tot))


def main():
    check_hashes()
    types = market_types()
    files = D.oos_files()
    print(f"unseen coins with data: {len(files)}")
    U = None
    out = {"window": [A, B], "pass_rule": PASS, "coins": len(files), "ideas": {}}
    for f in IDEAS:
        m = I.load_idea(ROOT / f)
        if m.KIND == "rule" and U is None:
            U = D.Universe(files)
        tr = I.idea_trades(m, {"files": files, "U": U}, types, A, B)
        s = I.summarize(tr)
        dd = daily(tr) if len(tr) else pd.Series(dtype=float)
        top = dd.sort_values(ascending=False).iloc[PASS["drop_top_days"]:] if len(dd) else dd
        s["day_avg_without_top3"] = float(top.mean()) if len(top) else None
        s["top3_days"] = {str(k.date()): float(v) for k, v in dd.sort_values(ascending=False).head(3).items()}
        if m.KIND == "rule":
            s["random_pct"], s["random_median_day_avg"] = random_pct(U, tr, m)
        ok = (s["trades"] >= PASS["min_trades"] and s["day_avg_pct"] > 0 and (s["day_t"] or 0) >= PASS["min_t"]
              and (s["pf_2x"] or 0) >= PASS["min_pf_2x"] and (s["day_avg_without_top3"] or 0) > 0)
        s["passed"] = bool(ok)
        out["ideas"][m.NAME] = s
        tr.to_parquet(HERE / f"trades_{Path(f).stem}.parquet")
        print(m.NAME, json.dumps({k: s.get(k) for k in ("trades", "days", "pf", "pf_2x", "day_avg_pct", "day_t",
                                                        "day_avg_without_top3", "random_pct", "passed")}, default=str))
    (HERE / "result.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
