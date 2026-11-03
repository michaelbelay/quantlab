"""Bear discovery: pick conditions on half A, test once on half B. Register: REGISTER_BEAR_DISCOVERY_2026-11-01.md.

    .venv\\Scripts\\python.exe research\\bear\\bear_discovery.py

Output: research/bear/discovery/rules_A.csv, picked.json, trades_<rule>.csv, report.json.
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
import bear_gates as bg  # noqa: E402

OUT = HERE / "discovery"
COINS, H, C, N, IDX, NC = b5.COINS, b5.H, b5.C, b5.N, b5.IDX, b6.NC
EL, COST = b6.EL, b5.COST
MID = bg.MID
A2_START = pd.Timestamp("2023-01-01", tz="UTC")
STOP, HOLD = 0.08, 72


def rank_prev(df: pd.DataFrame, n: int) -> pd.DataFrame:
    return df.apply(lambda s: b5.rank_prev(s, n))


def features() -> dict[str, np.ndarray]:
    r1h = C / C.shift(1) - 1
    dly = b6.daily_panel
    F = {"r1": C / C.shift(24) - 1, "r3": C / C.shift(72) - 1, "r7": C / C.shift(168) - 1, "r30": C / C.shift(720) - 1}
    F["rel7"] = F["r7"].sub(F["r7"]["BTC"], axis=0)
    F["d20"] = C / dly(20) - 1
    F["d50"] = C / dly(50) - 1
    F["vol7"] = r1h.rolling(168, min_periods=168).std()
    F["volr"] = F["vol7"] / r1h.rolling(720, min_periods=720).std()
    F["fund"] = b5.FUND_AT.ffill()
    F["fund7"] = b5.FUND_AT.fillna(0).rolling(168, min_periods=168).sum()
    qv = C * b5.bx.V
    F["vr"] = qv.rolling(24).sum() / (qv.rolling(720).sum() / 30)
    dc = C[b5.DAILY]
    d = dc.diff()
    up = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    F["rsi"] = (100 - 100 / (1 + up / dn.replace(0, np.nan))).reindex(H).ffill()
    F["hi30"] = C / b5.bx.Hi.rolling(720, min_periods=720).max() - 1
    F["lo30"] = C / b5.bx.Lo.rolling(720, min_periods=720).min() - 1
    bs24, bs7 = {}, {}
    for c in COINS:
        f = pd.read_feather(b5.ROOT / "data" / "market" / "flow" / f"{c}.feather").drop_duplicates("date").set_index("date").sort_index()
        f.index = pd.to_datetime(f.index, utc=True)
        s24 = f.taker_buy_quote.rolling(24).sum() / f.quote_volume.rolling(24).sum()
        s7 = f.taker_buy_quote.rolling(168).sum() / f.quote_volume.rolling(168).sum()
        # ranks only needed at daily closes: compute on the daily-close sample to keep it fast
        bs24[c] = s24.reindex(H)
        bs7[c] = s7.reindex(H)
    for name, src in (("bs24", bs24), ("bs7", bs7)):
        df = pd.DataFrame(src)
        F[name] = df.rolling(721, min_periods=721).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True)
    out = {k: v.to_numpy() for k, v in F.items()}
    btc = C["BTC"]
    rep = lambda s: np.repeat(np.asarray(s)[:, None], NC, 1)  # noqa: E731
    out["b_r1"] = rep(btc / btc.shift(24) - 1)
    out["b_r7"] = rep(btc / btc.shift(168) - 1)
    out["deep"] = rep(b6.deep_next().astype(float))
    dv = pd.read_csv(b5.ROOT / "data" / "market" / "dvol" / "BTC.csv").set_index("t").close
    dv.index = pd.to_datetime(dv.index, utc=True).normalize()
    dv = dv[~dv.index.duplicated()].sort_index()
    use = H.normalize() - pd.Timedelta(days=1)
    out["dvol_rk"] = rep(b5.rank_prev(dv, 90).reindex(use).to_numpy())
    out["dvol_chg"] = rep(dv.reindex(use).to_numpy() / dv.reindex(use - pd.Timedelta(days=3)).to_numpy() - 1)
    out["dow"] = rep(H.dayofweek.astype(float))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    F = features()
    sample = np.repeat((b5.DAILY & b5.BEAR_NEXT)[:, None], NC, 1) & EL
    ii, kk = np.nonzero(sample)
    res = []
    for i, k in zip(ii, kk):
        t = b5.single(k, i, -1, STOP, HOLD)
        res.append(np.nan if t is None else t[1])
    S = pd.DataFrame({"i": ii, "k": kk, "t": H[ii], "net": res})
    for f, a in F.items():
        S[f] = a[ii, kk]
    S = S.dropna(subset=["net"])
    A = S[S.t < MID]
    # buckets from half A
    rules = {}
    for f in F:
        if f in ("deep",):
            for v in (0.0, 1.0):
                rules[f"{f}=={int(v)}"] = (f, S[f].to_numpy() == v)
            continue
        if f == "dow":
            for v in range(7):
                rules[f"dow=={v}"] = (f, S[f].to_numpy() == v)
            continue
        edges = np.nanquantile(A[f], [0.2, 0.4, 0.6, 0.8])
        b = np.digitize(S[f].to_numpy(), edges)
        b = np.where(np.isnan(S[f].to_numpy()), -1, b)
        for q in range(5):
            rules[f"{f}#q{q + 1}[{(edges[q - 1] if q else -np.inf):.4g},{(edges[q] if q < 4 else np.inf):.4g})"] = (f, b == q)
    isA = (S.t < MID).to_numpy()
    isA1 = isA & (S.t < A2_START).to_numpy()
    isA2 = isA & (S.t >= A2_START).to_numpy()
    net = S.net.to_numpy()

    def screen(name, feats, m):
        ma = m & isA
        n = ma.sum()
        if n < 100:
            return None
        x = net[ma]
        mu, sd = x.mean(), x.std(ddof=1)
        if mu < 0.005 or net[m & isA1].mean() <= 0 or net[m & isA2].mean() <= 0 or not (m & isA2).any():
            return None
        return {"rule": name, "feats": feats, "n_A": int(n), "avg_A": mu, "t_A": mu / sd * np.sqrt(n),
                "avg_2022": net[m & isA1].mean(), "avg_2023_24": net[m & isA2].mean()}

    rows = []
    names = list(rules)
    for r in names:
        x = screen(r, [rules[r][0]], rules[r][1])
        if x:
            rows.append(x)
    for r1, r2 in itertools.combinations(names, 2):
        if rules[r1][0] == rules[r2][0]:
            continue
        x = screen(f"{r1} & {r2}", [rules[r1][0], rules[r2][0]], rules[r1][1] & rules[r2][1])
        if x:
            rows.append(x)
    Q = pd.DataFrame(rows).sort_values("t_A", ascending=False)
    Q.to_csv(OUT / "rules_A.csv", index=False)
    picked, used = [], set()
    for r in Q.itertuples():
        if used & set(r.feats):
            continue
        picked.append(r.rule)
        used |= set(r.feats)
        if len(picked) == 3:
            break
    (OUT / "picked.json").write_text(json.dumps({"picked": picked, "qualified_on_A": len(Q), "screened": len(names) + len(names) * (len(names) - 1) // 2,
                                                  "top10_A": Q.head(10).round(4).to_dict("records")}, indent=1, default=str), encoding="utf-8")
    print("qualified on A:", len(Q), "picked:", picked)

    # test on half B (proper trades), then step 2 on the full period
    rep = {}
    for name in picked:
        m = np.ones(len(S), bool)
        for part in name.split(" & "):
            m &= rules[part][1]
        sig = np.zeros((N, NC), bool)
        sig[S.i.to_numpy()[m], S.k.to_numpy()[m]] = True
        trs, paths = b6.run_single(sig, -1, STOP, hold=HOLD)
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
        trs.sort_values("net").to_csv(OUT / f"trades_{len(rep) + 1}.csv", index=False)
        rep[name] = r
        print(name, json.dumps(r, ensure_ascii=False))
    (OUT / "report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
