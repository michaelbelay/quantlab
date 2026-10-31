"""Scanner improvement loop - test ideas 2-6 of IDEAS_QUEUE.md in one pass (2026-10-13, Michael: "dont stop ...
treat it as test").

    .venv\\Scripts\\python.exe research\\opportunity\\ideas_test.py

Same data and bar as postmortem.py: the scanner's own cached candles (live_cache/, from 2026-04-20) and the live
forward record (forward.db). Each idea vs the rule as it is:
    confirm   enter one hour later, only if that hour did not move against the trade
    calm      skip signals while |BTC z24| > 1
    liquid    only coins whose 24h traded value is above the median of the watched coins at that hour
    half      half the time limit
    no6       skip hours where 6+ coins fire the same rule
Writes ideas_test.json. Changes nothing.
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
from postmortem import CACHE, HIST_START, load  # noqa: E402

IDEAS = ("confirm", "calm", "liquid", "half", "no6", "reverse")
OUT = HERE / "ideas_test.json"


def stats(s: pd.DataFrame) -> dict:
    if not len(s):
        return {"n": 0}
    da = s.groupby("day").ret.mean()
    t = da.mean() / da.std(ddof=1) * np.sqrt(len(da)) if len(da) > 2 and da.std(ddof=1) > 0 else None
    return {"n": len(s), "avg_pct": round(s.ret.mean(), 3), "day_avg_pct": round(da.mean(), 3),
            "t_day": None if t is None else round(t, 2), "win_pct": round((s.ret > 0).mean() * 100, 1)}


def main() -> None:
    book = json.loads((HERE / "playbook.json").read_text(encoding="utf-8"))
    bdf, bfu = load("BTCUSDT")
    bx = compute_conditions(regular_grid(bdf), bfu).set_index("date")
    btc_z = bx["z24"]

    ev, value = [], {}                                              # value: coin -> 24h traded value series
    for f in sorted(CACHE.glob("*_1h.feather")):
        sid = f.name[:-len("_1h.feather")]
        df, fund = load(sid)
        if df is None or len(df) < 800:
            continue
        try:
            x = compute_conditions(regular_grid(df), fund)
        except Exception:
            continue
        value[sid] = pd.Series((x["volume"] * x["close"]).rolling(24).sum().to_numpy(), index=x["date"])
        o, c = x["open"].to_numpy(float), x["close"].to_numpy(float)
        for name, rule in book["conditions"].items():
            idx = triggers(x[name].fillna(False).astype(bool))
            if not len(idx):
                continue
            idx = idx[(x["date"].iloc[idx] >= HIST_START).to_numpy()]
            idx = idx[idx + 2 + 48 <= len(x)]                       # room for the confirm entry too
            sig = x["sigma24"].to_numpy()[idx]
            ok = np.isfinite(sig) & (sig > 0)
            idx, sig = idx[ok], sig[ok]
            if not len(idx):
                continue
            d = 1 if rule["direction"] == "LONG" else -1
            H, T, S = rule["hours"], rule["target_sigma"], rule["stop_sigma"]
            _, P = paths(x, idx)
            base = simulate(P, sig, d, H, T, S)[0]
            half = simulate(P, sig, d, max(1, H // 2), T, S)[0]
            rev = simulate(P, sig, -d, H, T, S)[0]                  # idea 7: the opposite side
            _, P2 = paths(x, idx + 1)                               # entry at open of i+2
            conf = simulate(P2, sig, d, H, T, S)[0]
            conf_ok = d * (c[idx + 1] - o[idx + 1]) >= 0            # the waiting hour did not go against us
            for j, i in enumerate(idx):
                ev.append((name, x["date"].iloc[i], sid, base[j] * 100, half[j] * 100,
                           conf[j] * 100 if conf_ok[j] else np.nan, rev[j] * 100))
        del x
    e = pd.DataFrame(ev, columns=["condition", "t", "coin", "ret", "ret_half", "ret_conf", "ret_rev"])
    e["day"] = e.t.dt.strftime("%Y-%m-%d")
    e["cluster"] = e.groupby(["condition", "t"]).coin.transform("count")
    e["btcz"] = btc_z.reindex(e.t).to_numpy()
    V = pd.DataFrame(value)
    med = V.median(axis=1)
    e["liquid"] = [V.at[t, s] > med.at[t] if t in V.index else False for t, s in zip(e.t, e.coin)]

    def variants(g: pd.DataFrame) -> dict:
        return {"as is": stats(g),
                "confirm": stats(g.dropna(subset=["ret_conf"]).assign(ret=lambda z: z.ret_conf)),
                "calm": stats(g[g.btcz.abs() <= 1]),
                "liquid": stats(g[g.liquid]),
                "half": stats(g.assign(ret=g.ret_half)),
                "no6": stats(g[g.cluster < 6]),
                "reverse": stats(g.assign(ret=g.ret_rev))}

    hist = {k: variants(g) for k, g in e.groupby("condition")}

    # ---- live record, re-simulated on cached candles the same way for every variant
    con = sqlite3.connect(f"file:{HERE / 'forward.db'}?mode=ro", uri=True)
    d = pd.read_sql("SELECT * FROM alerts WHERE status IN ('target','stop','time')", con)
    con.close()
    d["cluster"] = d.groupby(["condition", "trigger_time"]).id.transform("count")
    cache, rows = {}, []
    for r in d.itertuples():
        sid = r.symbol.split("/")[0] + "USDT"
        if sid not in cache:
            cache[sid] = load(sid)[0]
        x = cache[sid]
        if x is None:
            continue
        te = pd.Timestamp(r.entry_time, unit="s", tz="UTC")
        w = x[x.date >= te].head(r.hours + 1)
        if len(w) < r.hours + 1:
            continue
        dirn = 1 if r.direction == "LONG" else -1
        T, S = r.tgt_pct / 100, r.stp_pct / 100

        def run(bars: pd.DataFrame, entry: float, hours: int, dirn: int = dirn) -> float:
            b = bars.head(hours)
            for hi_, lo_ in zip(b.high, b.low):
                fav = hi_ / entry - 1 if dirn == 1 else 1 - lo_ / entry
                adv = 1 - lo_ / entry if dirn == 1 else hi_ / entry - 1
                if adv >= S:
                    return (-S - COST_RT) * 100
                if fav >= T:
                    return (T - COST_RT) * 100
            return (dirn * (b.close.iloc[-1] / entry - 1) - COST_RT) * 100

        first = w.iloc[0]
        conf = (run(w.iloc[1:], w.open.iloc[1], r.hours)
                if dirn * (first.close - first.open) >= 0 else np.nan)
        tt = pd.Timestamp(r.trigger_time, unit="s", tz="UTC")
        vt = V.loc[:tt].iloc[-1] if len(V.loc[:tt]) else None
        rows.append({"condition": r.condition, "day": te.strftime("%Y-%m-%d"),
                     "ret": run(w, r.entry, r.hours), "ret_half": run(w, r.entry, max(1, r.hours // 2)),
                     "ret_conf": conf, "ret_rev": run(w, r.entry, r.hours, -dirn), "cluster": r.cluster, "btcz": btc_z.asof(tt),
                     "liquid": bool(vt is not None and sid in vt and vt[sid] > vt.median())})
    lv = pd.DataFrame(rows)
    live = {k: variants(g) for k, g in lv.groupby("condition")}

    verdict = []
    for k in hist:
        hb, lb = hist[k]["as is"], (live.get(k) or {}).get("as is", {"n": 0})
        for v in IDEAS:
            h, l_ = hist[k][v], (live.get(k) or {}).get(v, {"n": 0})
            if not h["n"] or not l_.get("n"):
                continue
            strict = (h["day_avg_pct"] > hb["day_avg_pct"] and h["day_avg_pct"] > 0 and (h["t_day"] or 0) >= 2
                      and l_["n"] >= 20 and l_["avg_pct"] > lb["avg_pct"] and l_["avg_pct"] > 0)
            both_better = (h["day_avg_pct"] > hb["day_avg_pct"] and h["day_avg_pct"] > 0
                           and l_["avg_pct"] > lb["avg_pct"] and l_["avg_pct"] > 0 and l_["n"] >= 10)
            verdict.append({"rule": k, "idea": v, "helps": strict, "positive_both": both_better,
                            "hist_as_is": hb["day_avg_pct"], "hist": h["day_avg_pct"], "t": h["t_day"],
                            "live_as_is": lb.get("avg_pct"), "live": l_["avg_pct"], "live_n": l_["n"],
                            "live_n_as_is": lb.get("n")})
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
           "history_events": len(e), "live_signals": len(lv), "history": hist, "live": live, "verdict": verdict}
    OUT.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(f"ideas 2-6: {len(e)} history events, {len(lv)} live signals")
    for v in verdict:
        if v["positive_both"]:
            print(f"  {'HELPS ' if v['helps'] else 'better'} {v['rule']:12} {v['idea']:8} hist {v['hist_as_is']} -> "
                  f"{v['hist']} (t {v['t']})  live {v['live_as_is']} -> {v['live']} (n {v['live_n']})")


if __name__ == "__main__":
    main()
