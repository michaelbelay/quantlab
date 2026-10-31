"""Opportunity engine - item 9: open-interest / positioning conditions (PREREGISTRATION_2026-10-07_oi.md).

30 desk coins, 1h bars from 15m klines, OI + ratios from 5m metrics. Same fit rule, simulator, costs and
badge as the playbook (functions imported, not copied). The sealed desk quadrant is filtered inside the
parquet read, so those rows are never loaded.

Run:  .venv\\Scripts\\python.exe research\\opportunity\\oi_study.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from common import compute_conditions, paths, regular_grid, triggers   # noqa: E402
from build_playbook import badge, fit_rule, stats, sub, window          # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DESK = ROOT / "data" / "market" / "desk"
OUT = Path(__file__).parent
SEALED = {"ETHUSDT", "SOLUSDT", "ENAUSDT", "SUIUSDT", "RAREUSDT", "TAOUSDT", "FILUSDT", "LTCUSDT", "1000PEPEUSDT",
          "QNTUSDT", "DASHUSDT", "ARKUSDT", "AAVEUSDT", "SAGAUSDT", "FETUSDT"}
SEAL_START = pd.Timestamp("2026-03-26", tz="UTC")
FIT_START, FIT_END, TEST_END = "2024-10-01", "2025-07-01", "2026-09-26"
PERIODS = [("p1_2024Q4_25Q1", "2024-10-01", "2025-04-01"), ("p2_2025Q2_Q3", "2025-04-01", "2025-10-01"),
           ("p3_2025Q4_26Q1", "2025-10-01", "2026-04-01"), ("p4_2026Q2_Q3", "2026-04-01", TEST_END)]
RANDOM_PER_COIN = 300
rng = np.random.default_rng(20261007)

OI_CONDITIONS = {
    "OI_BUILD_UP":   "open interest jumped (>= 3x normal 4h change) while price rose",
    "OI_BUILD_DN":   "open interest jumped (>= 3x normal 4h change) while price fell",
    "OI_FLUSH_DN":   "open interest collapsed while price fell hard (long-liquidation proxy)",
    "OI_FLUSH_UP":   "open interest collapsed while price rose hard (short-squeeze proxy)",
    "TAKER_BUY_X":   "aggressive (taker) buying at a 30-day extreme",
    "TAKER_SELL_X":  "aggressive (taker) selling at a 30-day extreme",
    "TOP_LONG_DIV":  "top accounts heavily long while the crowd is heavily short",
    "TOP_SHORT_DIV": "top accounts heavily short while the crowd is heavily long",
}


def read(coin: str, name: str) -> pd.DataFrame:
    filters = [("date", "<", SEAL_START)] if coin in SEALED else None     # sealed rows never leave the file
    return pd.read_parquet(DESK / coin / f"{name}.parquet", filters=filters)


def load(coin: str) -> pd.DataFrame:
    k = read(coin, "klines_15m")
    k["date"] = pd.to_datetime(k["date"], utc=True).astype("datetime64[ns, UTC]")
    h = (k.set_index("date").resample("1h")
         .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
         .dropna(subset=["close"]).reset_index())
    f = read(coin, "funding").rename(columns={"rate": "funding_rate"})[["date", "funding_rate"]]
    f["date"] = pd.to_datetime(f["date"], utc=True).astype("datetime64[ns, UTC]")
    x = compute_conditions(regular_grid(h), f)
    m = read(coin, "metrics_5m")
    m["date"] = pd.to_datetime(m["date"], utc=True).astype("datetime64[ns, UTC]")
    m = m.set_index("date").sort_index()
    m = m[~m.index.duplicated(keep="last")]
    # value at the last 5m stamp inside each hour; that hour's bar closes at date + 1h
    mh = m.resample("1h").last()
    mh = mh.reindex(pd.DatetimeIndex(x["date"]))
    for col in ("oi", "taker_ls", "top_ls_positions", "global_ls"):
        x[col] = mh[col].to_numpy()
    return x


def oi_conditions(x: pd.DataFrame) -> pd.DataFrame:
    oi = x["oi"].where(x["oi"] > 0)
    doi4 = np.log(oi / oi.shift(4))
    zoi = doi4 / doi4.rolling(720, min_periods=500).std()
    lc = np.log(x["close"])
    z4 = (lc - lc.shift(4)) / (x["sigma24"] * np.sqrt(4 / 24))
    pct = lambda s: s.rolling(720, min_periods=500).rank(pct=True)
    tk = pct(x["taker_ls"].rolling(4, min_periods=4).mean())
    top, crowd = pct(x["top_ls_positions"]), pct(x["global_ls"])
    c = pd.DataFrame(index=x.index)
    c["OI_BUILD_UP"] = (zoi >= 3) & (z4 >= 1)
    c["OI_BUILD_DN"] = (zoi >= 3) & (z4 <= -1)
    c["OI_FLUSH_DN"] = (zoi <= -3) & (z4 <= -1.5)
    c["OI_FLUSH_UP"] = (zoi <= -3) & (z4 >= 1.5)
    c["TAKER_BUY_X"] = tk >= 0.99
    c["TAKER_SELL_X"] = tk <= 0.01
    c["TOP_LONG_DIV"] = (top >= 0.95) & (crowd <= 0.05)
    c["TOP_SHORT_DIV"] = (top <= 0.05) & (crowd >= 0.95)
    valid = x["sigma24"].notna() & (x["volume"] > 0)
    return c.fillna(False).astype(bool) & valid.to_numpy()[:, None]


def collect():
    coins = [c["symbol"] for c in json.loads((DESK / "universe.json").read_text(encoding="utf-8"))["coins"]]
    bucket = {k: [] for k in list(OI_CONDITIONS) + ["_RANDOM"]}
    used = []
    for n, coin in enumerate(coins, 1):
        if not (DESK / coin / "metrics_5m.parquet").exists():
            print(f"  {coin}: no metrics file, unavailable", flush=True)
            continue
        x = load(coin)
        c = oi_conditions(x)
        used.append(coin)
        sig = x["sigma24"].to_numpy()
        dates = x["date"].dt.tz_localize(None).to_numpy()
        start = np.datetime64(FIT_START)
        for name in list(OI_CONDITIONS) + ["_RANDOM"]:
            if name == "_RANDOM":
                ok = np.flatnonzero(~np.isnan(sig) & (x["volume"].to_numpy() > 0) & (dates >= start))
                idx = np.sort(rng.choice(ok, size=min(RANDOM_PER_COIN, len(ok)), replace=False)) if len(ok) else ok
            else:
                idx = triggers(c[name])
                idx = idx[dates[idx] >= start]
            idx, P = paths(x, idx)
            if P is None:
                continue
            bucket[name].append({"coin": np.full(len(idx), coin), "date": dates[idx + 1],
                                 "trig": dates[idx], "sigma": sig[idx].astype(np.float64), **P})
        print(f"  {n}/{len(coins)} {coin}" + (" (sealed rows excluded)" if coin in SEALED else ""), flush=True)
    merged = {k: {f: np.concatenate([p[f] for p in parts]) for f in parts[0]} for k, parts in bucket.items() if parts}
    return merged, used


def event_avg(E: dict, rule: dict) -> tuple[float | None, int]:
    """Average per event (same condition, same trigger hour; coins averaged first)."""
    from common import simulate
    if len(E["sigma"]) == 0:
        return None, 0
    net, _, _ = simulate(E, E["sigma"], rule["dir"], rule["H"], rule["tgt"], rule["stp"])
    ev = pd.Series(net).groupby(pd.to_datetime(E["trig"])).mean()
    return round(float(ev.mean()) * 100, 3), int(len(ev))


def main():
    t0 = time.time()
    data, used = collect()
    R = data["_RANDOM"]
    out = {"built": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
           "preregistration": "PREREGISTRATION_2026-10-07_oi.md", "coins_used": len(used),
           "fit_window": [FIT_START, FIT_END], "test_window": [FIT_END, TEST_END], "trials": 6 * len(OI_CONDITIONS),
           "conditions": {}}
    rows = []
    for name, desc in OI_CONDITIONS.items():
        if name not in data:
            print(f"{name}: no triggers")
            continue
        E = data[name]
        fitE, testE = sub(E, window(E, FIT_START, FIT_END)), sub(E, window(E, FIT_END, TEST_END))
        if len(fitE["sigma"]) < 30:
            out["conditions"][name] = {"description": desc, "badge": "RED",
                                       "badge_why": [f"too few fit cases ({len(fitE['sigma'])})"]}
            print(f"{name:13s} fit n={len(fitE['sigma'])} -> RED (too few)")
            continue
        rule = fit_rule(fitE)
        fit, test = stats(fitE, rule), stats(testE, rule)
        base_test = stats(sub(R, window(R, FIT_END, TEST_END)), rule)
        reg = {pn: stats(sub(E, window(E, a, b)), rule) for pn, a, b in PERIODS}
        rpos = sum(1 for v in reg.values() if v.get("n", 0) >= 10 and v["avg_net_pct"] > 0)
        ev_avg, ev_n = event_avg(testE, rule)
        b, why = badge(fit, test, base_test, rpos)
        why = [w.replace("regimes", "periods") for w in why]
        if b != "RED" and (ev_avg is None or ev_avg <= 0):
            why = [w for w in why if not w.startswith("passes all")] + [f"test event-avg {ev_avg}% <= 0"]
            b = "ORANGE"
        out["conditions"][name] = {
            "description": desc, "direction": "LONG" if rule["dir"] == 1 else "SHORT", "hours": rule["H"],
            "target_sigma": rule["tgt"], "stop_sigma": rule["stp"], "fit": fit, "test": test,
            "random_test": base_test, "test_events": ev_n, "test_event_avg_pct": ev_avg,
            "periods": reg, "periods_positive": rpos, "badge": b, "badge_why": why}
        rows.append([name, "LONG" if rule["dir"] == 1 else "SHORT", rule["H"], rule["tgt"], rule["stp"], fit["n"],
                     fit["avg_net_pct"], test["n"], ev_n, test["avg_net_pct"], ev_avg, test["median_net_pct"],
                     test["t_day"], base_test["avg_net_pct"], rpos, b])
        print(f"{name:13s} {rows[-1][1]:5s} {rule['H']:>2}h | fit n={fit['n']:4d} {fit['avg_net_pct']:+.3f}% | "
              f"test n={test['n']:4d} ev={ev_n:4d} {test['avg_net_pct']:+.3f}% ev-avg {ev_avg:+.3f}% "
              f"t {test['t_day']:+.2f} rand {base_test['avg_net_pct']:+.3f}% | per {rpos}/4 -> {b}", flush=True)
    (OUT / "oi_playbook.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    pd.DataFrame(rows, columns=["condition", "dir", "hours", "tgt_sigma", "stp_sigma", "fit_n", "fit_avg_pct",
                                "test_n", "test_events", "test_avg_pct", "test_event_avg_pct", "test_median_pct",
                                "test_t_day", "random_test_avg_pct", "periods_pos", "badge"]
                 ).to_csv(OUT / "oi_summary.csv", index=False)
    print(f"done in {time.time() - t0:.0f}s, {len(used)} coins -> oi_playbook.json, oi_summary.csv")


if __name__ == "__main__":
    main()
