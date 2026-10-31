"""Channel UP_HIVOL (602db68df71a) redesign for the 300 USDT account, 2026-10-09.

Fixed before any result of this script was seen (hash in channel_redesign.sha256).

0. DATA FIX. channel_sim.py counted trades on coins whose price was frozen (open = high = low = close bar after
   bar, e.g. AIA: delisted / halted). ATR ~ 0 there, so the 8-ATR stop sits at entry and the "trade" closes one bar
   later for the fees (-0.15%). No real market exists, so these are removed: a signal is DEAD when the entry bar
   or 12+ of the previous 24 bars have high == low, or atr_pct < 0.0001. Applies to dev and unseen alike.

1. Designs (all 1x, position = realised equity / K, Binance min notional, same coin never twice, signals in time
   order; ties inside one hour broken by the design's priority, remaining ties random, 20 seeds):
   B   baseline, cleaned:              K = 5, random priority          (= channel_sim.py after the data fix)
   S   more, smaller slots:            K = 10, 15, 20, 30, random priority
   P   priority inside the hour:       K = 5 and K = 20, each with priority = highest 24h quote volume (liquid
                                       first) | lowest atr_pct (calm first) | highest engine score
   C   daily cap (spread over the day): K = 20, at most 5 new entries per UTC day, random priority
   = 13 designs.

2. Choice on DEVELOPMENT coins only (in-sample for this idea). A design qualifies when the median seed ends above
   300, at least 4 of 6 years are positive and the median max drawdown < 40%. The qualifier with the highest
   median final is THE choice. If none qualifies: stop, report, no unseen run.

3. One look at the UNSEEN coins for the choice only (the other 12 are printed for information AFTER the choice is
   fixed; they cannot change it). Same rule. Note: the unseen coins were already used once for this idea
   (UNSEEN3_RESULT_2026-10-09.md), so a pass here is weaker evidence and can give at most 🟡 pending forward test.

Limitation (same as channel_sim): realised equity only; open-trade swings are not marked.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "research"), str(ROOT / "research" / "engine"), str(ROOT / "research" / "incubator"),
                str(ROOT / "research" / "cap300")]
import downtrend as D  # noqa: E402
import incubator as I  # noqa: E402
from regime_switch import market_types  # noqa: E402
from sim import min_notionals  # noqa: E402

CID, A, B = "602db68df71a", "2021-01-01", "2026-09-25"
OUT = ROOT / "research" / "cap300"
SEEDS = 20

DESIGNS = [("B  K5 random", 5, None, None)]
DESIGNS += [(f"S  K{k} random", k, None, None) for k in (10, 15, 20, 30)]
DESIGNS += [(f"P  K{k} {p}", k, p, None) for k in (5, 20) for p in ("liquid", "calm", "score")]
DESIGNS += [("C  K20 cap5/day", 20, None, 5)]


def engine_trades(files) -> pd.DataFrame:
    import backtest as BT
    R = I.load_idea(ROOT / "research" / "pipeline" / "run.py")
    con = sqlite3.connect(f"file:{ROOT / 'research' / 'pipeline' / 'pipeline.db'}?mode=ro", uri=True)
    s, c = con.execute("select spec, cfg from candidates where id=?", (CID,)).fetchone()
    spec, cfg = json.loads(s), R.to_cfg(json.loads(c))
    rows = []
    for coin, p, fp in files:
        try:
            f = R.load(p, fp)
        except Exception:
            continue
        if f is None:
            continue
        dates = pd.to_datetime(f.date, utc=True)
        flat = (f.high == f.low)
        flat24 = pd.Series(flat.astype(int)).rolling(24, min_periods=1).sum().to_numpy()
        qv24 = pd.Series(f.df["volume"].to_numpy(float) * f.close).rolling(24, min_periods=1).sum().to_numpy()
        atrp = f.atr_pct.to_numpy(float)
        with np.errstate(all="ignore"):
            trades = BT.simulate_pair(f, spec, cfg, coin)
        for t in trades:
            if t.reason == "eod" or not t.notional:
                continue
            i = t.entry_i
            dead = bool(flat[i + 1] or flat24[i] >= 12 or atrp[i] < 1e-4)
            rows.append((coin, dates[i], dates[t.exit_i], t.pnl / t.notional * 100, t.score, atrp[i], qv24[i], dead))
    tr = pd.DataFrame(rows, columns=["coin", "entry", "exit", "pnl", "score", "atr_pct", "qv24", "dead"])
    tr = tr[(tr.entry >= pd.Timestamp(A, tz="UTC")) & (tr.entry < pd.Timestamp(B, tz="UTC"))]
    types = market_types()
    return tr[(tr.entry.dt.floor("D").map(types) == "UP_HIVOL").to_numpy()].reset_index(drop=True)


def account(tr, K, prio, cap, seed, minn) -> dict:
    rng = np.random.default_rng(seed)
    key = {"liquid": -tr.qv24, "calm": tr.atr_pct, "score": -tr.score}.get(prio, pd.Series(0.0, index=tr.index))
    tr = tr.assign(k=key.to_numpy(), r=rng.random(len(tr))).sort_values(["entry", "k", "r"])
    equity, open_, taken, per_day = 300.0, [], [], {}
    path = []
    for e in tr.itertuples():
        still = []
        for x in sorted(open_, key=lambda x: x[0]):
            if x[0] <= e.entry:
                equity += x[1]
                path.append((x[0], equity))
            else:
                still.append(x)
        open_ = still
        if equity <= 0:
            break
        day = e.entry.floor("D")
        if len(open_) >= K or any(o[2] == e.coin for o in open_) or (cap and per_day.get(day, 0) >= cap):
            continue
        notional = equity / K
        if notional < minn.get(e.coin, 5.0):
            continue
        pnl = notional * e.pnl / 100
        open_.append((e.exit, pnl, e.coin))
        taken.append((e.entry, pnl, e.pnl))
        per_day[day] = per_day.get(day, 0) + 1
    for x in sorted(open_, key=lambda x: x[0]):
        equity += x[1]
        path.append((x[0], equity))
    p = pd.DataFrame(path, columns=["t", "eq"]).set_index("t")["eq"] if path else pd.Series([300.0])
    t = pd.DataFrame(taken, columns=["entry", "usdt", "pct"])
    yrs = t.groupby(t.entry.dt.year).usdt.sum() if len(t) else pd.Series(dtype=float)
    return {"final": float(equity), "max_dd": float(-(p / p.cummax().clip(lower=300) - 1).min()),
            "taken": len(t), "win": float((t.pct > 0).mean() * 100) if len(t) else 0.0,
            "years": {int(y): round(float(v), 1) for y, v in yrs.items()}}


def evaluate(tr, design, minn) -> dict:
    name, K, prio, cap = design
    runs = [account(tr, K, prio, cap, s, minn) for s in range(SEEDS)]
    fin = np.array([r["final"] for r in runs])
    dd = np.array([r["max_dd"] for r in runs])
    med = runs[int(np.argsort(fin)[len(fin) // 2])]
    ypos = sum(v > 0 for v in med["years"].values())
    ok = bool(np.median(fin) > 300 and ypos >= 4 and np.median(dd) < 0.40)
    return {"name": name, "final_med": float(np.median(fin)), "final_min": float(fin.min()),
            "final_max": float(fin.max()), "dd_med": float(np.median(dd)), "dd_worst": float(dd.max()),
            "taken": med["taken"], "win": med["win"], "years": med["years"], "ypos": ypos, "ok": ok}


def line(r) -> str:
    return (f"  {r['name']:<20} final {r['final_med']:7.1f} ({r['final_min']:.0f}..{r['final_max']:.0f}) "
            f"DD {r['dd_med']:.0%} (worst {r['dd_worst']:.0%}) taken {r['taken']:5d} win {r['win']:.0f}% "
            f"yrs+ {r['ypos']}/6 {'PASS' if r['ok'] else '-'}\n      years {r['years']}")


def summary(name, tr):
    d = tr[tr.dead]
    print(f"\n=== {name}: {len(tr)} signals, {int(tr.dead.sum())} DEAD removed "
          f"(their mean {d.pnl.mean() if len(d) else 0:+.2f}%), live mean {tr[~tr.dead].pnl.mean():+.2f}%/trade")
    return tr[~tr.dead].reset_index(drop=True)


def main():
    minn = min_notionals()
    dev = summary("DEVELOPMENT coins", engine_trades(D.dev_files()))
    dev.to_parquet(OUT / "channel_redesign_dev.parquet")
    res = [evaluate(dev, d, minn) for d in DESIGNS]
    for r in res:
        print(line(r))
    passers = [r for r in res if r["ok"]]
    if not passers:
        print("\nNo design qualifies on development coins -> stop, no unseen run.")
        json.dump({"dev": res, "choice": None}, open(OUT / "channel_redesign.json", "w"), indent=1)
        return
    choice = max(passers, key=lambda r: r["final_med"])["name"]
    print(f"\nCHOICE (fixed on dev): {choice}")
    oos = summary("UNSEEN coins (second use)", engine_trades(D.oos_files()))
    oos.to_parquet(OUT / "channel_redesign_unseen.parquet")
    chosen = evaluate(oos, next(d for d in DESIGNS if d[0] == choice), minn)
    print("CHOICE on unseen:\n" + line(chosen))
    print(f"VERDICT: {'PASS' if chosen['ok'] else 'FAIL'}")
    print("\nOther designs on unseen (information only, cannot change the verdict):")
    other = [evaluate(oos, d, minn) for d in DESIGNS if d[0] != choice]
    for r in other:
        print(line(r))
    json.dump({"dev": res, "choice": choice, "unseen_choice": chosen, "unseen_other": other},
              open(OUT / "channel_redesign.json", "w"), indent=1)


if __name__ == "__main__":
    main()
