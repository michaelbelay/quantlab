"""Bear batch 11: OI round 2 (P1-P5) + OI discovery (learn half A, test half B). Register: REGISTER_BEAR_OI2_2026-11-02.md.

    .venv\\Scripts\\python.exe research\\bear\\bear_oi2.py

Output: research/bear/batch11/trades_<idea>.csv, rules_A.csv, report.json. Nothing here is tuned after the run.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bear_batch5 as b5  # noqa: E402
import bear_batch6 as b6  # noqa: E402
import bear_discovery as bd  # noqa: E402
import bear_gates as bg  # noqa: E402
import bear_oi as bo  # noqa: E402

OUT = HERE / "batch11"
COINS, H, C, N, IDX, NC = b5.COINS, b5.H, b5.C, b5.N, b5.IDX, b6.NC
EL, COST, MID = b6.EL, b5.COST, bg.MID
OI_FEATS = {"oi24", "oi72", "oi7d", "oi_rk", "oi_vol_rk", "ls_rk", "top_rk", "taker_rk"}


def finish(rep, name, tr, paths):
    tr.sort_values("net").to_csv(OUT / f"trades_{name}.csv", index=False)
    rep[name] = bg.stats(tr)
    if rep[name]["verdict"] == "🟠":
        s1, s2 = bg.step2(paths, N, H, COST, 1), bg.step2(paths, N, H, COST, 2)
        rep[name]["step2"], rep[name]["step2_2x"] = s1, s2
        rep[name]["verdict"] = "🟡" if (s1["profit_usdt"] > 0 and s2["profit_usdt"] > 0 and s1["max_dd_pct"] >= -35
                                       and s1["worst_trade_usdt"] >= -30) else "🟠"
    print(name, json.dumps(rep[name], ensure_ascii=False), flush=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    oi = bo.hourly("oi_usdt")
    ls, top, tk = bo.hourly("ls_accounts"), bo.hourly("top_ls_positions"), bo.hourly("taker_ls_vol")
    has = oi.notna().to_numpy()
    bear = np.repeat(b5.BEAR_NEXT[:, None], NC, 1)
    base = bear & EL & has
    below = (C < C.rolling(480, min_periods=480).mean()).to_numpy()
    r7 = (C / C.shift(168) - 1).to_numpy()
    r72 = (C / C.shift(72) - 1).to_numpy()
    qv24 = (C * b5.bx.V).rolling(24, min_periods=24).sum()
    oi_rk = bo.rank_prev(oi)
    oi_vol_rk = bo.rank_prev(oi / qv24)
    rep = {}

    s = bo.gap_signal(base & (oi_rk.to_numpy() >= 0.95) & below & (r7 < 0), 72)
    finish(rep, "P1_leverage_peak_downtrend", *b6.run_single(s, -1, 0.08, hold=72))

    s = bo.gap_signal(base & (oi_vol_rk.to_numpy() >= 0.90) & below, 72)
    finish(rep, "P2_leverage_vs_activity", *b6.run_single(s, -1, 0.08, hold=72))

    fund = b5.FUND_AT.ffill().to_numpy()
    oi72 = (oi / oi.shift(72) - 1).to_numpy()
    s = bo.gap_signal(base & (fund >= 0.0001) & (oi72 >= 0.15) & (r72 <= 0), 72)
    finish(rep, "P3_trapped_longs", *b6.run_single(s, -1, 0.08, hold=72))

    lo168, hi168 = oi.rolling(168, min_periods=168).min(), oi.rolling(168, min_periods=168).max()
    s = bo.gap_signal(base & (lo168 <= 0.80 * hi168).to_numpy() & (oi >= 1.10 * lo168).to_numpy() & below, 72)
    finish(rep, "P4_releverage_after_flush", *b6.run_single(s, -1, 0.08, hold=72))

    oi7 = (oi / oi.shift(168) - 1).to_numpy()
    s = bo.gap_signal(base & (r7 >= 0.05) & (oi7 <= -0.10) & below, 72)
    finish(rep, "P5_weak_weekly_rally", *b6.run_single(s, -1, 0.08, hold=72))

    # ---- part 2: OI discovery
    F = bd.features()
    F.update({"oi24": (oi / oi.shift(24) - 1).to_numpy(), "oi72": oi72, "oi7d": oi7, "oi_rk": oi_rk.to_numpy(),
              "oi_vol_rk": oi_vol_rk.to_numpy(), "ls_rk": bo.rank_prev(ls).to_numpy(), "top_rk": bo.rank_prev(top).to_numpy(),
              "taker_rk": bo.rank_prev(tk.rolling(24, min_periods=24).mean()).to_numpy()})
    sample = np.repeat((b5.DAILY & b5.BEAR_NEXT)[:, None], NC, 1) & EL & has
    ii, kk = np.nonzero(sample)
    res = [(lambda t: np.nan if t is None else t[1])(b5.single(k, i, -1, bd.STOP, bd.HOLD)) for i, k in zip(ii, kk)]
    S = pd.DataFrame({"i": ii, "k": kk, "t": H[ii], "net": res})
    for f, a in F.items():
        S[f] = a[ii, kk]
    S = S.dropna(subset=["net"])
    A = S[S.t < MID]
    rules = {}
    for f in F:
        if f == "deep":
            for v in (0.0, 1.0):
                rules[f"deep=={int(v)}"] = (f, S[f].to_numpy() == v)
            continue
        if f == "dow":
            for v in range(7):
                rules[f"dow=={v}"] = (f, S[f].to_numpy() == v)
            continue
        if A[f].notna().sum() < 500:
            continue
        edges = np.nanquantile(A[f], [0.2, 0.4, 0.6, 0.8])
        x = S[f].to_numpy()
        b = np.where(np.isnan(x), -1, np.digitize(x, edges))
        for q in range(5):
            rules[f"{f}#q{q + 1}[{(edges[q - 1] if q else -np.inf):.4g},{(edges[q] if q < 4 else np.inf):.4g})"] = (f, b == q)
    isA = (S.t < MID).to_numpy()
    isA1 = isA & (S.t < bd.A2_START).to_numpy()
    isA2 = isA & (S.t >= bd.A2_START).to_numpy()
    net = S.net.to_numpy()

    def screen(name, feats, m):
        if not (OI_FEATS & set(feats)):
            return None
        ma = m & isA
        n = int(ma.sum())
        if n < 100 or not (m & isA1).any() or not (m & isA2).any():
            return None
        x = net[ma]
        mu = x.mean()
        if mu < 0.005 or net[m & isA1].mean() <= 0 or net[m & isA2].mean() <= 0:
            return None
        return {"rule": name, "feats": feats, "n_A": n, "avg_A": mu, "t_A": mu / x.std(ddof=1) * np.sqrt(n),
                "avg_2022": net[m & isA1].mean(), "avg_2023_24": net[m & isA2].mean()}

    rows = []
    names = list(rules)
    for r in names:
        x = screen(r, [rules[r][0]], rules[r][1])
        if x:
            rows.append(x)
    for r1, r2 in itertools.combinations(names, 2):
        if rules[r1][0] != rules[r2][0]:
            x = screen(f"{r1} & {r2}", [rules[r1][0], rules[r2][0]], rules[r1][1] & rules[r2][1])
            if x:
                rows.append(x)
    Q = pd.DataFrame(rows).sort_values("t_A", ascending=False)
    Q.to_csv(OUT / "rules_A.csv", index=False)
    picked, used = [], set()
    for r in Q.itertuples():
        if not used & set(r.feats):
            picked.append(r.rule)
            used |= set(r.feats)
        if len(picked) == 3:
            break
    print("qualified on A:", len(Q), "picked:", picked, flush=True)
    for name in picked:
        m = np.ones(len(S), bool)
        for part in name.split(" & "):
            m &= rules[part][1]
        sig = np.zeros((N, NC), bool)
        sig[S.i.to_numpy()[m], S.k.to_numpy()[m]] = True
        trs, paths = b6.run_single(sig, -1, bd.STOP, hold=bd.HOLD)
        B = trs[trs.entry >= MID]
        mB = B.groupby(B.entry.dt.strftime("%Y-%m")).net.sum()
        totB = B.net.sum()
        top3 = 100 * mB.nlargest(3).sum() / totB if totB > 0 else None
        wo10 = B.net.sort_values().iloc[:-10].mean() if len(B) > 10 else np.nan
        r = {"trades_A": int((trs.entry < MID).sum()), "avg_A": round(100 * trs[trs.entry < MID].net.mean(), 3),
             "trades_B": len(B), "avg_B": round(100 * B.net.mean(), 3) if len(B) else None,
             "avg_B_2x": round(100 * B.net2x.mean(), 3) if len(B) else None,
             "months_pos_B": f"{int((mB > 0).sum())}/{len(mB)}", "top3_B_pct": None if top3 is None else round(top3, 1),
             "avg_B_wo_top10": round(100 * wo10, 3) if wo10 == wo10 else None,
             "years": {str(y): [len(g), round(100 * g.net.mean(), 2)] for y, g in trs.groupby(trs.entry.dt.year)},
             "worst_B": [(x.coin, str(x.entry)[:10], round(100 * x.net, 2)) for x in B.nsmallest(3, "net").itertuples()]}
        ok = (len(B) >= 50 and B.net.mean() >= 0.003 and B.net2x.mean() > 0 and (mB > 0).mean() >= 0.55
              and wo10 == wo10 and wo10 > 0 and top3 is not None and top3 <= 50)
        r["B_pass"] = bool(ok)
        if ok:
            s1, s2 = bg.step2(paths, N, H, COST, 1), bg.step2(paths, N, H, COST, 2)
            r["step2"], r["step2_2x"] = s1, s2
            r["verdict"] = "🟡" if (s1["profit_usdt"] > 0 and s2["profit_usdt"] > 0 and s1["max_dd_pct"] >= -35
                                   and s1["worst_trade_usdt"] >= -30) else "🟠"
        else:
            r["verdict"] = "🔴"
        trs.sort_values("net").to_csv(OUT / f"trades_disc_{len([k for k in rep if k.startswith('disc')]) + 1}.csv", index=False)
        rep[f"disc: {name}"] = r
        print(name, json.dumps(r, ensure_ascii=False), flush=True)
    (OUT / "report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
