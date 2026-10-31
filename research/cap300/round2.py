"""CAP300 Round 2 (ROUND2_2026-10-04.md): single-asset trend generality test + risk-adjusted momentum."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[0] / "pipeline")]
import designs as DS  # noqa: E402
import run_round as RR  # noqa: E402
import sim as SM  # noqa: E402

COST = 0.0010


def sa_weights(D, coins, lb=20, long_only=True, every=1, target=0.40, cap=2.0):
    c = D["close"][coins]
    sig = np.sign(c / c.shift(lb) - 1)
    if long_only:
        sig = sig.clip(lower=0)
    vol = D["ret"][coins].rolling(30, min_periods=20).std() * np.sqrt(365)
    W = (sig * (target / vol)).clip(-cap, cap)
    W = W.where(c.notna(), 0).fillna(0.0)
    return DS.hold_every(W, every)


def per_coin(W, D, coins, cost=COST, rng=None, reps=0):
    """Per-coin daily strategy returns (single-asset account, fractional sizing) and stats."""
    ret = D["ret"][coins].fillna(0.0)
    fund = D["funding"][coins].fillna(0.0)
    held = W.shift(1).fillna(0.0)
    turn = (W - W.shift(1).fillna(0.0)).abs().shift(1).fillna(0.0)
    r = held * ret - held * fund - turn * cost
    out = {}
    for col in coins:
        s = r[col][D["close"][col].notna()]
        if len(s) < 120 or held[col].abs().sum() == 0:
            continue
        h = held[col].reindex(s.index)
        # trades: contiguous same-sign holdings
        sg = np.sign(h.to_numpy())
        tr, acc, cur = [], 0.0, 0
        for v, x in zip(sg, s.to_numpy()):
            if v != cur:
                if cur != 0:
                    tr.append(acc)
                acc, cur = 0.0, v
            if cur != 0:
                acc += x
        if cur != 0:
            tr.append(acc)
        eq = (1 + s).cumprod()
        o = {"total": float(eq.iloc[-1] - 1), "sharpe": float(s.mean() / s.std() * np.sqrt(365)) if s.std() > 0 else 0.0,
             "max_dd": float(-(eq / eq.cummax() - 1).min()), "trades": tr, "days": len(s)}
        if reps:
            # sign randomisation: each holding period gets a random direction, exposure schedule unchanged
            seg = np.cumsum(np.r_[1, (np.diff(sg) != 0)])
            base = (np.abs(h.to_numpy()) * ret[col].reindex(s.index).to_numpy())
            fu = (np.abs(h.to_numpy()) * fund[col].reindex(s.index).to_numpy())
            tc = (turn[col].reindex(s.index).to_numpy() * cost)
            nseg = seg.max()
            finals = []
            for _ in range(reps):
                flip = rng.choice([-1.0, 1.0], size=nseg + 1)[seg]
                rr = flip * base - flip * fu - tc
                finals.append(np.prod(1 + rr) - 1)
            o["rand_pct"] = float((np.array(finals) < o["total"]).mean() * 100)
        out[col] = o
    return out


def summarize_sa(res: dict, res2: dict) -> dict:
    tr = np.concatenate([np.array(v["trades"]) for v in res.values()]) if res else np.array([])
    tr2 = np.concatenate([np.array(v["trades"]) for v in res2.values()]) if res2 else np.array([])
    pf = lambda a: float(a[a > 0].sum() / -a[a < 0].sum()) if (a < 0).any() else None
    pos = np.mean([v["total"] > 0 for v in res.values()])
    beat = np.mean([v.get("rand_pct", 0) >= 95 for v in res.values()])
    return {"coins": len(res), "share_positive": float(pos), "pooled_pf": pf(tr), "pooled_pf_2x": pf(tr2),
            "median_sharpe": float(np.median([v["sharpe"] for v in res.values()])),
            "median_total": float(np.median([v["total"] for v in res.values()])),
            "median_dd": float(np.median([v["max_dd"] for v in res.values()])),
            "share_beat_random_p95": float(beat), "trades": int(len(tr))}


def class_sa(s):
    if s["share_positive"] >= 0.60 and (s["pooled_pf"] or 0) >= 1.10 and s["share_beat_random_p95"] >= 0.25 and (s["pooled_pf_2x"] or 0) >= 1.05:
        return "G"
    if s["share_positive"] >= 0.55 and (s["pooled_pf"] or 0) >= 1.05:
        return "Y"
    if s["share_positive"] > 0.50 or (s["pooled_pf"] or 0) > 1.0:
        return "O"
    return "R"


def ram(D, coins, k=30, n=5, gross=0.5, lb=60):
    inpool, lr = DS.pool(D, coins, k)
    c = D["close"][coins]
    score = (c / c.shift(lb) - 1) / (D["ret"][coins].rolling(lb, min_periods=40).std() * np.sqrt(lb))
    exit_ = c < D["low"][coins].rolling(20).min().shift(1)
    cand = inpool & (score > 0) & ~exit_
    rk = score.where(cand).rank(axis=1, ascending=False)
    sel = rk <= n
    W = sel.astype(float) * (gross / n)
    return W.mul(DS.btc_on(D), axis=0)


def main():
    P = RR.panels()
    rng = np.random.default_rng(20261005)
    minn = SM.min_notionals()
    out = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "A": [], "A_deploy": [], "B": {}}
    D = P["unseen"]
    coins = [c for c in D["close"].columns if c != "BTC"]
    for name, kw in (("SA-L", dict(long_only=True)), ("SA-LS", dict(long_only=False)),
                     ("SA-L-W", dict(long_only=True, every=7)), ("SA-LS-W", dict(long_only=False, every=7))):
        W = sa_weights(D, coins, **kw).loc["2021-01-01":]
        res = per_coin(W, D.copy() if False else D, coins, rng=rng, reps=200)
        res2 = per_coin(W, D, coins, cost=2 * COST)
        s = summarize_sa(res, res2)
        s["class"] = class_sa(s)
        s["design"] = name
        out["A"].append(s)
        print(f"{name:8} unseen coins {s['coins']}: positive {s['share_positive']:.0%} | pooled PF {s['pooled_pf']:.3f} (2x {s['pooled_pf_2x']:.3f}) | "
              f"median Sharpe {s['median_sharpe']:.2f} | median total {s['median_total']:+.0%} | median DD {s['median_dd']:.0%} | "
              f"beat sign-random p95: {s['share_beat_random_p95']:.0%} | {RR.CLASS[s['class']]}", flush=True)
    # deployable form on BTC / ETH / SOL (development coins: reference)
    L = P["live"]
    maj = [c for c in ("BTC", "ETH", "SOL") if c in L["close"].columns]
    for name, kw in (("SA-L", dict(long_only=True)), ("SA-LS", dict(long_only=False)),
                     ("SA-L-W", dict(long_only=True, every=7)), ("SA-LS-W", dict(long_only=False, every=7))):
        W = sa_weights(L, maj, **kw).loc["2021-01-01":] / len(maj)          # one third of the account per coin
        m = SM.metrics(SM.simulate(W, L, minn=minn))
        m2 = SM.metrics(SM.simulate(W, L, minn=minn, cost_mult=2.0))
        m.pop("daily")
        m["final_2x"], m["pf_2x"], m["design"] = m2["final"], m2["pf"], name
        out["A_deploy"].append(m)
        print(f"  deploy {name:8} BTC/ETH/SOL @300: final {m['final']:.0f} (2x {m['final_2x']:.0f}) CAGR {m['cagr']:+.1%} DD {m['max_dd']:.0%} "
              f"PF {m['pf'] or 0:.2f} | 2021 {m['reg_2021']:+.0%} 2022 {m['reg_2022']:+.0%} 23-24 {m['reg_2023_24']:+.0%} 25-26 {m['reg_2025_26']:+.0%} "
              f"| skipped {m['skipped_orders']}", flush=True)
    # Redesign B on the unseen coins
    W = ram(D, coins).loc["2021-01-01":]
    m = SM.metrics(SM.simulate(W, D, minn=minn))
    m2 = SM.metrics(SM.simulate(W, D, minn=minn, cost_mult=2.0))
    finals = np.array([SM.simulate(DS.random_twin(W, D, coins, 30, rng), D, minn=minn)["equity"].iloc[-1] for _ in range(200)])
    m["random_pct"], m["pf_2x"], m["final_2x"] = float((finals < m["final"]).mean() * 100), m2["pf"], m2["final"]
    m.pop("daily")
    cls, fails = RR.classify(m)
    m["class"], m["fails"] = cls, fails
    out["B"] = m
    print(f"RAM-K30-N5-G50 unseen @300: final {m['final']:.0f} (2x {m['final_2x']:.0f}) PF {m['pf'] or 0:.2f} DD {m['max_dd']:.0%} CAGR {m['cagr']:+.1%} "
          f"rnd p{m['random_pct']:.0f} (median twin {np.median(finals):.0f}) | 2021 {m['reg_2021']:+.0%} 2022 {m['reg_2022']:+.0%} "
          f"23-24 {m['reg_2023_24']:+.0%} 25-26 {m['reg_2025_26']:+.0%} | {RR.CLASS[cls]}", flush=True)
    (HERE / "round2_results.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print("ROUND2_COMPLETE")


if __name__ == "__main__":
    main()
