"""ML model on FlowTrend's 20 coins. Rule: ../REGISTER_ML_FLOW_2026-10-28.md (registered before this run).

    .venv\\Scripts\\python.exe research\\fresh\\ml_flow\\run.py
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT / "data" / "market" / "main" / "binance" / "futures"
FLOW = ROOT / "data" / "market" / "flow"
COINS = [p.split("/")[0] for p in json.loads((HERE.parent / "strat_bt/FlowTrend/config.json").read_text())["exchange"]["pair_whitelist"]]
HOLD, STOP_K, FEE, SLOTS, WALLET = 48, 2.0, 0.0005, 6, 300.0
P_LONG, P_SHORT = 0.60, 0.40
FEATS = ["z24", "z6", "r4", "r24", "r72", "r240", "rel72", "sig24", "vrel", "fund", "fund3d", "btc24", "btc240", "fng"]


def fng() -> pd.Series:
    f = HERE / "fng.json"
    if not f.exists():
        f.write_bytes(urllib.request.urlopen("https://api.alternative.me/fng/?limit=0", timeout=30).read())
    d = pd.DataFrame(json.loads(f.read_text())["data"])
    s = pd.Series(d.value.astype(float).values, index=pd.to_datetime(d.timestamp.astype(int), unit="s", utc=True)).sort_index()
    s.index = s.index + pd.Timedelta(days=1)                 # yesterday's value is known today
    return s


def coin_frame(c: str, btc: pd.DataFrame | None) -> pd.DataFrame:
    d = pd.read_feather(DATA / f"{c}_USDT_USDT-1h-futures.feather").drop_duplicates("date").set_index("date").sort_index()
    q = pd.read_feather(FLOW / f"{c}.feather").drop_duplicates("date").set_index("date").sort_index()
    q.index = pd.to_datetime(q.index, utc=True)
    d = d.join(q[["quote_volume", "taker_buy_quote"]], how="left")
    lc = np.log(d.close)
    d["sig24"] = lc.diff().rolling(720, min_periods=500).std() * np.sqrt(24)
    for h in (4, 24, 72, 240):
        d[f"r{h}"] = lc - lc.shift(h)
    for w, name in ((24, "z24"), (6, "z6")):
        sh = d.taker_buy_quote.rolling(w).sum() / d.quote_volume.rolling(w).sum().replace(0, np.nan)
        d[name] = (sh - sh.rolling(720, min_periods=500).mean()) / sh.rolling(720, min_periods=500).std()
    qv = d.close * d.volume
    d["vrel"] = qv.rolling(24).sum() / (qv.rolling(720, min_periods=500).mean() * 24)
    fr = DATA / f"{c}_USDT_USDT-1h-funding_rate.feather"
    if fr.exists():
        f = pd.read_feather(fr).drop_duplicates("date").set_index("date").sort_index()["funding_rate"]
        f = f.reindex(d.index, method="ffill")
        d["fund"], d["fund3d"] = f, f.rolling(72, min_periods=24).mean()
    else:
        d["fund"] = d["fund3d"] = np.nan
    if btc is not None:
        d["btc24"], d["btc240"] = btc["r24"].reindex(d.index), btc["r240"].reindex(d.index)
        d["rel72"] = d["r72"] - btc["r72"].reindex(d.index)
    d["fwd"] = d.close.shift(-HOLD) / d.close - 1
    d["coin"] = c
    return d


def main() -> None:
    btc = coin_frame("BTC", None)
    btc["btc24"], btc["btc240"], btc["rel72"] = btc["r24"], btc["r240"], 0.0
    frames = {c: (btc if c == "BTC" else coin_frame(c, btc)) for c in COINS}
    g = fng()
    for d in frames.values():
        d["fng"] = g.reindex(d.index, method="ffill").values
    # monthly top-10 by last calendar month's traded value
    val = pd.DataFrame({c: (d.close * d.volume).resample("MS").sum() for c, d in frames.items()})
    top = {m: set(val.loc[:m - pd.Timedelta(days=1)].iloc[-1].nlargest(10).index) for m in val.index[1:]}
    rows = pd.concat([d[(d.index.hour + 1) % 4 == 0] for d in frames.values()]).dropna(subset=["fwd", "z24", "r240", "sig24"])
    rows = rows.reset_index().rename(columns={"index": "date"})
    rows["y"] = (rows.fwd > 0).astype(int)
    preds = []
    for m in pd.period_range("2024-04", "2026-09", freq="M"):
        m0 = m.start_time.tz_localize("UTC")
        m1 = (m + 1).start_time.tz_localize("UTC")
        tr = rows[rows.date + pd.Timedelta(hours=HOLD + 1) <= m0]
        te = rows[(rows.date >= m0) & (rows.date < m1)].copy()
        te = te[te.coin.isin(top.get(m0, set()))]
        if te.empty:
            continue
        mdl = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=200,
                                             random_state=0).fit(tr[FEATS], tr.y)
        te["p"] = mdl.predict_proba(te[FEATS])[:, 1]
        preds.append(te)
        print(m, "train", len(tr), "test", len(te), flush=True)
    P = pd.concat(preds)
    P.to_csv(HERE / "predictions.csv", index=False)
    sig = P[(P.p >= P_LONG) | (P.p <= P_SHORT)].copy()
    sig["short"] = sig.p <= P_SHORT
    sig["conf"] = (sig.p - 0.5).abs()
    sig = sig.sort_values(["date", "conf"], ascending=[True, False])
    # simulate
    bal, opened, last_sig, trades = WALLET, [], {}, []
    for _, s in sig.iterrows():
        t = s.date
        for o in [o for o in opened if o["exit_t"] <= t]:
            bal += o["usdt"]; opened.remove(o)
        key = (s.coin, s.short)
        if key in last_sig and t - last_sig[key] < pd.Timedelta(hours=24):
            continue
        last_sig[key] = t
        if len(opened) >= SLOTS:
            continue
        d = frames[s.coin]
        i = d.index.get_loc(t)
        e, k = d.close.iat[i], STOP_K * d.sig24.iat[i]
        fut = d.iloc[i + 1:i + 1 + HOLD]
        if len(fut) < HOLD:
            continue
        stop = e * (1 + k) if s.short else e * (1 - k)
        hit = (fut.high >= stop) if s.short else (fut.low <= stop)
        if hit.any():
            j = int(np.argmax(hit.values)); px, why = stop, "stop"
        else:
            j = HOLD - 1; px, why = fut.close.iat[-1], "time_48h"
        r = (1 - px / e) if s.short else (px / e - 1)
        stake = bal / SLOTS
        net = r - 2 * FEE
        o = {"coin": s.coin, "short": bool(s.short), "p": round(s.p, 3), "open": t, "exit_t": fut.index[j] + pd.Timedelta(hours=1),
             "ret": net, "stake": stake, "usdt": stake * net, "exit": why}
        opened.append(o); trades.append(o)
    for o in opened:
        bal += o["usdt"]
    T = pd.DataFrame(trades).sort_values("exit_t")
    T.to_csv(HERE / "trades.csv", index=False)
    eq = WALLET + T.usdt.cumsum()
    dd = float((eq / eq.cummax() - 1).min())
    w, l = T[T.usdt > 0], T[T.usdt <= 0]
    T["y"] = T.open.dt.year
    out = {"trades": len(T), "avg_pct": round(T.ret.mean() * 100, 2), "win_pct": round((T.usdt > 0).mean() * 100, 1),
           "avg_win_usdt": round(w.usdt.mean(), 2), "avg_loss_usdt": round(l.usdt.mean(), 2),
           "trades_10plus": int((T.usdt >= 10).sum()), "worst_usdt": round(T.usdt.min(), 2), "best_usdt": round(T.usdt.max(), 2),
           "final": round(bal, 2), "max_dd_pct": round(dd * 100, 1), "stops": int((T.exit == "stop").sum()),
           "by_year": {int(k): round(v, 1) for k, v in T.groupby("y").usdt.sum().items()},
           "long": [int((~T.short).sum()), round(T[~T.short].ret.mean() * 100, 2)],
           "short": [int(T.short.sum()), round(T[T.short].ret.mean() * 100, 2)],
           "signals_p_ge_060": int((P.p >= P_LONG).sum()), "signals_p_le_040": int((P.p <= P_SHORT).sum()), "rows_predicted": len(P)}
    (HERE / "result.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out))


if __name__ == "__main__":
    main()
