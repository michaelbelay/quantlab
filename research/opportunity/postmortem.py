"""Opportunity engine - post-mortem: why signals passed or failed, and which fixes would have helped.

2026-10-13, Michael: "search why they have been failed and why others passed ... work on improving the strategies
on the loop and work on automation". Runs daily (Task Scheduler "Quantlab Signal Postmortem") and on demand:

    .venv\\Scripts\\python.exe research\\opportunity\\postmortem.py

Part 1 - LIVE (forward.db): every closed signal gets a reason, from its own candles in live_cache/:
    passed     target hit                          -> with the market (BTC moved the same way) / against it
    near miss  stopped after getting >= 70% of the way to target
    market     stopped while BTC moved >= 1% against the trade (the whole market took it out)
    fast stop  stopped within 2 hours (entered at the wrong moment)
    coin       stopped for reasons of the coin itself
    time up    neither hit inside the time limit
Part 2 - IDEAS, checked on HISTORY: each rule as it is, and with a fixed list of changes, re-run on the scanner's
own cached candles (live_cache/, the coins the scanner really watches, from mid-April 2026 when the 30-day
volatility is first known). A change is only listed as "helps" if it beats the rule as it is on history AND
on the live record. Nothing here changes a rule or a badge: a change that helps becomes a proposal for Michael.

Fixed list of changes (stated before any result, 2026-10-13):
    market   longs only while BTC's 24h return > 0, shorts only while < 0
    solo     skip hours where 3+ coins fire the same rule (one market move, not coin news)
    both     market + solo
Coins are today's top list (survivor bias) and the history overlaps the playbook's 2025-26 test window.
The 280 unseen coins are not read.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from common import COST_RT, compute_conditions, paths, regular_grid, simulate, triggers  # noqa: E402

CACHE = HERE / "live_cache"
OUT = HERE / "postmortem.json"
HIST_START = pd.Timestamp("2026-04-20", tz="UTC")
VARIANTS = ("as is", "market", "solo", "both")
# Loop ideas that change the EXITS (IDEAS_QUEUE.md): name -> (target multiplier, stop multiplier).
# Judged against "as is" computed the same way (live: re-simulated on cached candles, costs, no funding).
EXIT_IDEAS = {"exits 0.75/1.25": (0.75, 1.25)}


def load(sid: str) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    f, fu = CACHE / f"{sid}_1h.feather", CACHE / f"{sid}_funding.feather"
    if not f.exists():
        return None, None
    df = pd.read_feather(f)
    df["date"] = pd.to_datetime(df["date"], utc=True).astype("datetime64[ns, UTC]")
    fund = pd.read_feather(fu) if fu.exists() else None
    if fund is not None:
        fund["date"] = pd.to_datetime(fund["date"], utc=True).astype("datetime64[ns, UTC]")
    return df, fund


def btc_series() -> pd.Series:
    b, _ = load("BTCUSDT")
    return b.set_index("date")["close"]


# ------------------------------------------------------------------ part 1: live reasons
def live(btc: pd.Series) -> dict:
    c = sqlite3.connect(f"file:{HERE / 'forward.db'}?mode=ro", uri=True)
    d = pd.read_sql("SELECT * FROM alerts WHERE status IN ('target','stop','time')", c)
    c.close()
    d["cluster"] = d.groupby(["condition", "trigger_time"]).id.transform("count")
    cache: dict[str, pd.DataFrame | None] = {}
    rows = []
    for r in d.itertuples():
        sid = r.symbol.split("/")[0] + "USDT"
        if sid not in cache:
            cache[sid] = load(sid)[0]
        x, dirn = cache[sid], 1 if r.direction == "LONG" else -1
        t0, t1 = pd.Timestamp(r.entry_time, unit="s", tz="UTC"), pd.Timestamp(r.exit_time, unit="s", tz="UTC")
        mfe = None
        if x is not None:
            w = x[(x.date >= t0) & (x.date <= t1)]
            if len(w):
                best = w.high.max() / r.entry - 1 if dirn == 1 else 1 - w.low.min() / r.entry
                mfe = best / (r.tgt_pct / 100)                       # share of the way to target
        b0, b1 = btc.asof(t0 - pd.Timedelta(hours=1)), btc.asof(t1)  # BTC close before entry -> close of exit bar
        bmove = dirn * (b1 / b0 - 1) * 100                          # + = BTC moved WITH the trade
        took = (r.exit_time - r.entry_time) / 3600 + 1
        if r.status == "target":
            why = "passed, with the market" if bmove >= 0 else "passed, against the market"
        elif r.status == "time":
            why = "time up"
        elif mfe is not None and mfe >= 0.7:
            why = "near miss"
        elif bmove <= -1:
            why = "market moved against"
        elif took <= 2:
            why = "fast stop"
        else:
            why = "coin itself"
        rows.append({"condition": r.condition, "direction": r.direction, "status": r.status, "ret": r.ret_pct,
                     "why": why, "btc_with_pct": round(bmove, 2), "mfe": None if mfe is None else round(mfe, 2),
                     "cluster": int(r.cluster), "day": t0.strftime("%Y-%m-%d")})
    f = pd.DataFrame(rows)
    out = {"n": len(f), "days": int(f.day.nunique()) if len(f) else 0, "rules": {}}
    if not len(f):
        return out
    out["reasons"] = f.why.value_counts().to_dict()
    for k, g in f.groupby("condition"):
        out["rules"][k] = {
            "direction": g.direction.iloc[0], "n": len(g), "avg_pct": round(g.ret.mean(), 2),
            "passed": int((g.status == "target").sum()), "failed": int((g.status == "stop").sum()),
            "time_up": int((g.status == "time").sum()), "reasons": g.why.value_counts().to_dict(),
            "with_market_avg": round(g[g.btc_with_pct >= 0].ret.mean(), 2) if (g.btc_with_pct >= 0).any() else None,
            "against_market_avg": round(g[g.btc_with_pct < 0].ret.mean(), 2) if (g.btc_with_pct < 0).any() else None,
            "variants": {v: variant_stats(g, v) for v in VARIANTS},
        }
    return out


def keep(v: str, btc_ret24: float, cluster: int, direction: str) -> bool:
    mk = (btc_ret24 > 0) if direction == "LONG" else (btc_ret24 < 0)
    so = cluster < 3
    return {"as is": True, "market": mk, "solo": so, "both": mk and so}[v]


def variant_stats(g: pd.DataFrame, v: str) -> dict | None:
    """Live record of a rule under a change. The market filter needs BTC's 24h return AT the signal."""
    if "btc24" not in g:
        return None
    k = g[[keep(v, b, c, dr) for b, c, dr in zip(g.btc24, g.cluster, g.direction)]]
    return {"n": len(k), "avg_pct": round(k.ret.mean(), 2) if len(k) else None}


# ------------------------------------------------------------------ part 2: history
def history(book: dict, btc: pd.Series) -> dict:
    btc24 = (btc / btc.shift(24) - 1)
    ev = []                                                         # every historical trigger, all rules
    for f in sorted(CACHE.glob("*_1h.feather")):
        sid = f.name[:-len("_1h.feather")]
        df, fund = load(sid)
        if df is None or len(df) < 800:
            continue
        try:
            x = compute_conditions(regular_grid(df), fund)
        except Exception:
            continue
        for name, rule in book["conditions"].items():
            idx = triggers(x[name].fillna(False).astype(bool))
            idx = idx[(x["date"].iloc[idx] >= HIST_START).to_numpy()] if len(idx) else idx
            idx, P = paths(x, idx)
            if P is None:
                continue
            sig = x["sigma24"].to_numpy()[idx]
            ok = np.isfinite(sig) & (sig > 0)
            if not ok.any():
                continue
            P = {k: v[ok] for k, v in P.items()}
            idx, sig = idx[ok], sig[ok]
            d = 1 if rule["direction"] == "LONG" else -1
            net, outc, _ = simulate(P, sig, d, rule["hours"], rule["target_sigma"], rule["stop_sigma"])
            extra = [simulate(P, sig, d, rule["hours"], rule["target_sigma"] * tm, rule["stop_sigma"] * sm)[:2]
                     for tm, sm in EXIT_IDEAS.values()]
            for j, (i, n_, o_) in enumerate(zip(idx, net, outc)):
                t = x["date"].iloc[i]
                ev.append((name, rule["direction"], t, sid, float(n_) * 100, int(o_),
                           *[v for en, eo in extra for v in (float(en[j]) * 100, int(eo[j]))]))
    ecols = [c for k in EXIT_IDEAS for c in (f"ret:{k}", f"out:{k}")]
    e = pd.DataFrame(ev, columns=["condition", "direction", "t", "coin", "ret", "out", *ecols])
    e["cluster"] = e.groupby(["condition", "t"]).coin.transform("count")
    e["btc24"] = btc24.reindex(e.t).to_numpy()
    e["day"] = e.t.dt.strftime("%Y-%m-%d")
    out = {"start": str(HIST_START.date()), "end": str(e.t.max().date()) if len(e) else None,
           "coins": int(e.coin.nunique()), "rules": {}}
    for k, g in e.groupby("condition"):
        res = {}
        for v in VARIANTS:
            s = g[[keep(v, b, c, dr) for b, c, dr in zip(g.btc24.fillna(0), g.cluster, g.direction)]]
            dayavg = s.groupby("day").ret.mean()
            res[v] = {"n": len(s), "days": int(s.day.nunique()), "avg_pct": round(s.ret.mean(), 3) if len(s) else None,
                      "day_avg_pct": round(dayavg.mean(), 3) if len(s) else None,
                      "t_day": round(dayavg.mean() / dayavg.std(ddof=1) * np.sqrt(len(dayavg)), 2) if len(dayavg) > 2 else None,
                      "target_pct": round((s.out == 1).mean() * 100, 1) if len(s) else None,
                      "stop_pct": round((s.out == -1).mean() * 100, 1) if len(s) else None}
        for name in EXIT_IDEAS:
            s = g.assign(ret=g[f"ret:{name}"], out=g[f"out:{name}"])
            dayavg = s.groupby("day").ret.mean()
            res[name] = {"n": len(s), "days": int(s.day.nunique()), "avg_pct": round(s.ret.mean(), 3),
                         "day_avg_pct": round(dayavg.mean(), 3),
                         "t_day": round(dayavg.mean() / dayavg.std(ddof=1) * np.sqrt(len(dayavg)), 2) if len(dayavg) > 2 else None,
                         "target_pct": round((s.out == 1).mean() * 100, 1), "stop_pct": round((s.out == -1).mean() * 100, 1)}
        out["rules"][k] = {"direction": g.direction.iloc[0], "variants": res}
    return out


def live_exits() -> dict:
    """Live record re-simulated on cached 1h candles: as is vs each EXIT_IDEAS change (stop first if both in a bar,
    exit at the close of the last allowed hour, COST_RT, no funding - the same method for both)."""
    c = sqlite3.connect(f"file:{HERE / 'forward.db'}?mode=ro", uri=True)
    d = pd.read_sql("SELECT * FROM alerts WHERE status IN ('target','stop','time')", c)
    c.close()
    cache, rows = {}, []
    for r in d.itertuples():
        sid = r.symbol.split("/")[0] + "USDT"
        if sid not in cache:
            cache[sid] = load(sid)[0]
        x = cache[sid]
        if x is None:
            continue
        w = x[x.date >= pd.Timestamp(r.entry_time, unit="s", tz="UTC")].head(r.hours)
        if len(w) < r.hours:
            continue
        dirn = 1 if r.direction == "LONG" else -1
        fav = (w.high / r.entry - 1).to_numpy() if dirn == 1 else (1 - w.low / r.entry).to_numpy()
        adv = (1 - w.low / r.entry).to_numpy() if dirn == 1 else (w.high / r.entry - 1).to_numpy()
        last = dirn * (w.close.iloc[-1] / r.entry - 1)
        res = {}
        for name, (tm, sm) in {"as is": (1.0, 1.0), **EXIT_IDEAS}.items():
            T, S = r.tgt_pct / 100 * tm, r.stp_pct / 100 * sm
            g = last
            for f_, a_ in zip(fav, adv):
                if a_ >= S:
                    g = -S
                    break
                if f_ >= T:
                    g = T
                    break
            res[name] = (g - COST_RT) * 100
        rows.append({"condition": r.condition, **res})
    f = pd.DataFrame(rows)
    return {k: {n: {"n": len(g), "avg_pct": round(g[n].mean(), 2)} for n in ["as is", *EXIT_IDEAS]}
            for k, g in f.groupby("condition")}


def add_btc24(btc: pd.Series) -> pd.Series:
    return btc / btc.shift(24) - 1


def main() -> None:
    if sys.stdout is None:                                          # pythonw (Task Scheduler): log to a file
        sys.stdout = sys.stderr = open(HERE / "postmortem.log", "a", encoding="utf-8", buffering=1)
        print(f"\n##### post-mortem {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC")
    book = json.loads((HERE / "playbook.json").read_text(encoding="utf-8"))
    btc = btc_series()
    lv = live(btc)
    # live variants need BTC 24h return at the signal hour: recompute with it
    c = sqlite3.connect(f"file:{HERE / 'forward.db'}?mode=ro", uri=True)
    d = pd.read_sql("SELECT condition, direction, trigger_time, ret_pct ret FROM alerts "
                    "WHERE status IN ('target','stop','time')", c)
    c.close()
    d["cluster"] = d.groupby(["condition", "trigger_time"]).ret.transform("count")
    b24 = add_btc24(btc)
    d["btc24"] = b24.reindex(pd.to_datetime(d.trigger_time, unit="s", utc=True)).to_numpy()
    d["btc24"] = d["btc24"].fillna(0)
    for k, g in d.groupby("condition"):
        if k in lv["rules"]:
            lv["rules"][k]["variants"] = {v: variant_stats(g, v) for v in VARIANTS}
    hi = history(book, btc)

    # verdict per rule and change: helps only if better than "as is" on history (day-avg, t >= 2) AND live (avg)
    proposals = []
    for k, h in hi["rules"].items():
        base_h = h["variants"]["as is"]
        base_l = lv["rules"].get(k, {}).get("variants", {}).get("as is") or {}
        for v in VARIANTS[1:]:
            hv = h["variants"][v]
            lvv = lv["rules"].get(k, {}).get("variants", {}).get(v) or {}
            if not hv["n"] or hv["day_avg_pct"] is None or base_h["day_avg_pct"] is None:
                continue
            better_h = hv["day_avg_pct"] > base_h["day_avg_pct"] and hv["day_avg_pct"] > 0 and (hv["t_day"] or 0) >= 2
            better_l = (lvv.get("avg_pct") is not None and base_l.get("avg_pct") is not None
                        and lvv["avg_pct"] > base_l["avg_pct"] and lvv["avg_pct"] > 0 and lvv["n"] >= 20)
            if better_h and better_l:
                proposals.append({"rule": k, "change": v, "history": hv, "live": lvv,
                                  "history_as_is": base_h, "live_as_is": base_l})
    lx = live_exits()
    ideas = {}
    for name in EXIT_IDEAS:
        ideas[name] = {}
        for k, h in hi["rules"].items():
            hv, hb = h["variants"][name], h["variants"]["as is"]
            lb, lvv = (lx.get(k) or {}).get("as is") or {}, (lx.get(k) or {}).get(name) or {}
            better_h = hv["day_avg_pct"] > hb["day_avg_pct"] and hv["day_avg_pct"] > 0 and (hv["t_day"] or 0) >= 2
            better_l = bool(lvv) and lvv["avg_pct"] > lb["avg_pct"] and lvv["avg_pct"] > 0 and lvv["n"] >= 20
            ideas[name][k] = {"history_as_is": hb, "history": hv, "live_as_is": lb, "live": lvv,
                              "helps": better_h and better_l}
            if better_h and better_l:
                proposals.append({"rule": k, "change": name, "history": hv, "live": lvv,
                                  "history_as_is": hb, "live_as_is": lb})
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "live": lv, "history": hi,
           "ideas": ideas,
           "proposals": proposals,
           "rule": "a change is proposed only if, versus the rule as it is, it has a higher positive day-average with "
                   "day t >= 2 on history AND a higher positive average over >= 20 live signals. Proposals change "
                   "nothing by themselves: Michael decides."}
    OUT.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(f"post-mortem: {lv['n']} live signals on {lv['days']} days, history {hi['start']}..{hi['end']} on "
          f"{hi['coins']} coins, {len(proposals)} proposals")
    for p in proposals:
        print(f"  PROPOSAL {p['rule']} + {p['change']}: history day-avg {p['history']['day_avg_pct']} "
              f"(as is {p['history_as_is']['day_avg_pct']}), live avg {p['live']['avg_pct']} (as is {p['live_as_is']['avg_pct']})")


if __name__ == "__main__":
    main()
