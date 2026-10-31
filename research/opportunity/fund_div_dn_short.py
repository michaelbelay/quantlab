"""FUND_DIV_DN short side (2026-10-15, Michael: "test the short side of fund div dn").

Condition (unchanged, common.py): funding in its top 5% (and > 0.01%) but the 24h move is <= -1.5x the normal daily
move. The scanner only ever tracked the LONG (bounce) side. Here: the SHORT side, with the LONG side next to it on
the same trades for comparison.

Universe = the coins the scanner would really scan, point in time: every local Binance USD-M 1h history (dead coins
included; data/market/dev_1h/binance/futures + data/market/extra_coins_1h, ~460 coins), and a trigger counts only if the coin was in the top 200 by 30-day traded value (close x volume) on the
day before the trigger. No unseen / held-out set is involved.

Rule per direction, chosen with the playbook's fixed method on the fit window (< 2025-01-01) only: time limit from
(8, 24, 48)h, target = median favourable move, stop = 80th pct adverse move of winners (sigma24 units). Costs 0.2%
round trip + real funding. Then frozen and run on 2025-01 -> data end.

Verdict (stated before results, = the playbook badge): RED if fit avg <= 0, test avg <= 0 or test n < 30; ORANGE if
positive but fails one of test day-t >= 2, beats random short entries by >= 0.10 pp, >= 3 of 4 regimes positive;
YELLOW if it passes all. Also shown: by year and by BTC market condition (Bull/Bear x Calm/Wild) and the live signals.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from common import FIT_END, HORIZONS, REGIMES, compute_conditions, paths, regular_grid, simulate, triggers  # noqa: E402
from build_playbook import badge, fit_rule, stats, sub, window  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FUT = ROOT / "data" / "market" / "dev_1h" / "binance" / "futures"
OOS = ROOT / "data" / "market" / "extra_coins_1h"


def sources() -> dict[str, tuple[Path, Path]]:
    src = {p.name.split("_USDT_USDT")[0]: (p, FUT / p.name.replace("-futures", "-funding_rate"))
           for p in FUT.glob("*_USDT_USDT-1h-futures.feather")}
    for d in OOS.iterdir():
        c = d.name[:-4] if d.name.endswith("USDT") else d.name
        if c not in src and (d / "ohlcv_1h.feather").exists():
            src[c] = (d / "ohlcv_1h.feather", d / "funding.feather")
    return src


SRC: dict[str, tuple[Path, Path]] = {}
TOP = 200
rng = np.random.default_rng(20261015)


def load(coin):
    pp, fp = SRC[coin]
    df = pd.read_feather(pp)
    return regular_grid(df), (pd.read_feather(fp) if fp.exists() else None)


def btc_condition() -> pd.Series:
    """Bull/Bear = BTC 20d return > 0; Wild/Calm = BTC 20d vol > its 365d median (same as the UI Today tab)."""
    b, _ = load("BTC")
    d = b.set_index("date")["close"].resample("1D").last().dropna()
    r20 = d / d.shift(20) - 1
    v20 = d.pct_change().rolling(20).std()
    med = v20.rolling(365, min_periods=300).median().shift(1)
    cell = np.where(r20 > 0, "Bull", "Bear") + np.where(v20 > med, "-Wild", "-Calm")
    s = pd.Series(cell, index=d.index)
    return s.where(med.notna())


def main():
    SRC.update(sources())
    coins = sorted(SRC)
    # pass 1: point-in-time top-200 by 30-day traded value
    val = {}
    for c in coins:
        x = pd.read_feather(SRC[c][0], columns=["date", "close", "volume"])
        x["date"] = pd.to_datetime(x["date"], utc=True)
        val[c] = (x["close"] * x["volume"]).groupby(x["date"].dt.floor("D")).sum()
    V = pd.DataFrame(val).sort_index().fillna(0.0)
    rank = V.rolling(30, min_periods=20).sum().shift(1).rank(axis=1, ascending=False)     # known the day before
    print(f"coins with history: {len(coins)}", flush=True)

    ev, rnd = [], []
    for n, c in enumerate(coins, 1):
        g, fund = load(c)
        if fund is None:
            continue
        x = compute_conditions(g, fund)
        day = x["date"].dt.floor("D")
        rk = rank[c].reindex(day).to_numpy()
        inuni = np.nan_to_num(rk, nan=1e9) <= TOP
        sig = x["sigma24"].to_numpy()
        dates = x["date"].dt.tz_localize(None).to_numpy()
        for bucket, idx in (("ev", triggers(x["FUND_DIV_DN"])), ("rnd", None)):
            if idx is None:
                ok = np.flatnonzero(~np.isnan(sig) & (x["volume"].to_numpy() > 0) & inuni)
                idx = np.sort(rng.choice(ok, size=min(150, len(ok)), replace=False)) if len(ok) else ok
            else:
                idx = idx[inuni[idx]]
            idx, P = paths(x, idx)
            if P is None:
                continue
            (ev if bucket == "ev" else rnd).append({"coin": np.full(len(idx), c), "date": dates[idx + 1],
                                                     "sigma": sig[idx].astype(np.float64), **P})
        if n % 50 == 0:
            print(f"  {n}/{len(coins)}", flush=True)
    E = {k: np.concatenate([p[k] for p in ev]) for k in ev[0]}
    R = {k: np.concatenate([p[k] for p in rnd]) for k in rnd[0]}
    print(f"FUND_DIV_DN triggers in the top-{TOP}: {len(E['sigma'])} on {len(set(E['coin']))} coins")

    fitE, testE = sub(E, window(E, end=FIT_END)), sub(E, window(E, start=FIT_END))
    cond = btc_condition()
    out = {}
    for d, name in ((-1, "SHORT"), (1, "LONG")):
        # the playbook's fixed method, restricted to one direction
        best = None
        for H in HORIZONS:
            s = fitE["sigma"]
            fav = (fitE["hi"][:, :H].max(1) if d == 1 else -fitE["lo"][:, :H].min(1)) / s
            adv = (-fitE["lo"][:, :H].min(1) if d == 1 else fitE["hi"][:, :H].max(1)) / s
            final = d * fitE["cl"][:, H - 1] / s
            tgt = float(max(np.median(fav), 0.3))
            w = adv[final > 0]
            stp = float(max(np.percentile(w, 80) if len(w) >= 10 else 1.0, 0.3))
            m = float(simulate(fitE, s, d, H, tgt, stp)[0].mean())
            if best is None or m > best["fit_avg"]:
                best = {"dir": d, "H": H, "tgt": round(tgt, 3), "stp": round(stp, 3), "fit_avg": m}
        rule = best
        fit, test = stats(fitE, rule), stats(testE, rule)
        base = stats(sub(R, window(R, start=FIT_END)), rule)
        reg = {rn: stats(sub(E, window(E, a, b)), rule) for rn, a, b in REGIMES}
        rpos = sum(1 for v in reg.values() if v.get("n", 0) >= 10 and v["avg_net_pct"] > 0)
        b, why = badge(fit, test, base, rpos)
        print(f"\n===== {name}: {rule['H']}h, target {rule['tgt']} x daily move, stop {rule['stp']} x daily move")
        for lab, st in (("fit 2021-24", fit), ("test 2025-26", test), ("random entries 2025-26", base)):
            print(f"  {lab:24s} n {st['n']:5d}  avg {st['avg_net_pct']:+.2f}%  median {st['median_net_pct']:+.2f}%  "
                  f"win {st['win_pct']:.0f}%  PF {st['pf']}  day-t {st['t_day']:+.2f}  days {st['days']}")
        print("  regimes:", " | ".join(f"{k} n {v.get('n', 0)} {v.get('avg_net_pct', 0):+.2f}%" for k, v in reg.items()))
        net, _, _ = simulate(E, E["sigma"], d, rule["H"], rule["tgt"], rule["stp"])
        t = pd.to_datetime(E["date"])
        df = pd.DataFrame({"t": t, "net": net * 100, "coin": E["coin"],
                           "cell": cond.reindex(t.floor("D").tz_localize("UTC")).to_numpy()})
        y = df.groupby(df.t.dt.year).net.agg(["size", "mean"])
        print("  by year:", " | ".join(f"{i}: {int(r['size'])} {r['mean']:+.2f}%" for i, r in y.iterrows()))
        cc = df.groupby("cell").net.agg(["size", "mean"])
        print("  by market:", " | ".join(f"{i}: {int(r['size'])} {r['mean']:+.2f}%" for i, r in cc.iterrows()))
        print(f"  verdict: {b}  {'; '.join(why)}")
        out[name] = (rule, df)
    return out


if __name__ == "__main__":
    main()
