"""Scalping families on 5m, FlowTrend's 20 coins. Rule: ../REGISTER_SCALP_2026-10-29.md (registered before this run).

    .venv\\Scripts\\python.exe research\\fresh\\scalp\\run.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view as swv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT / "data" / "market" / "main" / "binance" / "futures"
COINS = [p.split("/")[0] for p in json.loads((HERE.parent / "strat_bt/FlowTrend/config.json").read_text())["exchange"]["pair_whitelist"]]
SLOTS, WALLET, START, END = 6, 300.0, "2024-02-03", "2026-09-30 23:55"
# family: (target kind, target ATR mult, stop ATR mult, max bars)
FAM = {"S1_bb_fade": ("mid", 0, 1.5, 12), "S2_trend_pullback": ("atr", 1.0, 1.5, 24), "S3_vol_breakout": ("atr", 1.5, 1.0, 12),
       "S4_spike_fade": ("atr", 1.0, 1.0, 6), "S5_vwap_fade": ("mid", 0, 1.5, 24)}


def rsi(c: pd.Series, n: int) -> pd.Series:
    d = c.diff()
    up, dn = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(), (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def signals(d: pd.DataFrame) -> dict[str, tuple[pd.Series, pd.Series, pd.Series | None]]:
    """family -> (long bool, short bool, target level for 'mid' kinds)"""
    c, h, l, v = d.close, d.high, d.low, d.volume
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    d["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    vm = v.shift().rolling(288).mean()
    out = {}
    mid, sd = c.rolling(20).mean(), c.rolling(20).std()
    r3 = rsi(c, 3)
    out["S1_bb_fade"] = ((c < mid - 2.5 * sd) & (r3 < 5), (c > mid + 2.5 * sd) & (r3 > 95), mid)
    e = c.ewm(span=600, adjust=False).mean()
    r2 = rsi(c, 2)
    out["S2_trend_pullback"] = ((e > e.shift(12)) & (c > e) & (r2 < 10), (e < e.shift(12)) & (c < e) & (r2 > 90), None)
    out["S3_vol_breakout"] = ((c > h.shift().rolling(12).max()) & (v > 3 * vm), (c < l.shift().rolling(12).min()) & (v > 3 * vm), None)
    big = ((h - l) > 4 * d.atr.shift()) & (v > 5 * vm)
    out["S4_spike_fade"] = (big & (c < d.open), big & (c > d.open), None)
    vw = (c * v).rolling(288).sum() / v.rolling(288).sum()
    out["S5_vwap_fade"] = (c < vw - 3 * d.atr, c > vw + 3 * d.atr, vw)
    return out


def outcomes(d: pd.DataFrame, idx: np.ndarray, short: bool, kind: str, tk: float, sk: float, H: int, mid: pd.Series | None):
    """resolve every signal bar idx -> (entry time, exit time, gross return)"""
    n = len(d)
    idx = idx[idx + H < n]
    o, hi, lo, cl = d.open.values, d.high.values, d.low.values, d.close.values
    a = d.atr.values[idx]
    e = o[idx + 1]
    if kind == "mid":
        tgt = mid.values[idx]
    else:
        tgt = e - tk * a if short else e + tk * a
    stop = e + sk * a if short else e - sk * a
    ok = (tgt < e) if short else (tgt > e)            # target already passed at entry -> skip
    idx, e, tgt, stop = idx[ok], e[ok], tgt[ok], stop[ok]
    W_hi, W_lo = swv(hi, H)[idx + 1], swv(lo, H)[idx + 1]
    hit_s = (W_hi >= stop[:, None]) if short else (W_lo <= stop[:, None])
    hit_t = (W_lo <= tgt[:, None]) if short else (W_hi >= tgt[:, None])
    js = np.where(hit_s.any(1), hit_s.argmax(1), H)
    jt = np.where(hit_t.any(1), hit_t.argmax(1), H)
    px = np.where(js <= jt, stop, tgt)                  # same bar -> stop first
    j = np.minimum(js, jt)
    timeout = j == H
    px = np.where(timeout, cl[idx + H], px)
    j = np.where(timeout, H - 1, j)
    r = (1 - px / e) if short else (px / e - 1)
    t = d.index.values
    why = np.where(timeout, "time", np.where(js <= jt, "stop", "target"))
    return pd.DataFrame({"open": t[idx + 1], "exit_t": t[idx + 1 + j] + np.timedelta64(5, "m"), "r": r, "short": short, "why": why})


def simulate(S: pd.DataFrame, fee: float) -> tuple[pd.DataFrame, float]:
    bal, opened, busy, trades = WALLET, [], set(), []
    for s in S.itertuples(index=False):
        for o in [o for o in opened if o["exit_t"] <= s.open]:
            bal += o["usdt"]; opened.remove(o); busy.discard(o["coin"])
        if s.coin in busy or len(opened) >= SLOTS:
            continue
        stake = bal / SLOTS
        net = s.r - 2 * fee
        o = {"coin": s.coin, "short": s.short, "open": s.open, "exit_t": s.exit_t, "ret": net, "usdt": stake * net, "why": s.why}
        opened.append(o); busy.add(s.coin); trades.append(o)
    for o in opened:
        bal += o["usdt"]
    return pd.DataFrame(trades), bal


def report(T: pd.DataFrame, bal: float) -> dict:
    if T.empty:
        return {"trades": 0}
    T = T.sort_values("exit_t")
    eq = WALLET + T.usdt.cumsum()
    w, l = T[T.usdt > 0], T[T.usdt <= 0]
    yr = pd.to_datetime(T.open).dt.year
    return {"trades": len(T), "avg_pct": round(T.ret.mean() * 100, 3), "win_pct": round((T.usdt > 0).mean() * 100, 1),
            "avg_win_usdt": round(w.usdt.mean(), 2), "avg_loss_usdt": round(l.usdt.mean(), 2),
            "trades_10plus": int((T.usdt >= 10).sum()), "worst_usdt": round(T.usdt.min(), 2), "best_usdt": round(T.usdt.max(), 2),
            "final": round(bal, 2), "max_dd_pct": round(float((eq / eq.cummax() - 1).min()) * 100, 1),
            "by_year": {int(k): round(v, 1) for k, v in T.usdt.groupby(yr).sum().items()},
            "long": [int((~T.short).sum()), round(T[~T.short].ret.mean() * 100, 3)],
            "short": [int(T.short.sum()), round(T[T.short].ret.mean() * 100, 3)],
            "exits": T.why.value_counts().to_dict()}


def main() -> None:
    sig = {f: [] for f in FAM}
    for c in COINS:
        d = pd.read_feather(DATA / f"{c}_USDT_USDT-5m-futures.feather").drop_duplicates("date").set_index("date").sort_index()
        d = d.loc[:END]
        fam = signals(d)
        pos = np.arange(len(d))
        live = d.index >= pd.Timestamp(START, tz="UTC")
        for f, (lg, sh, mid) in fam.items():
            kind, tk, sk, H = FAM[f]
            for side, m in ((False, lg), (True, sh)):
                idx = pos[(m.fillna(False).values) & live]
                o = outcomes(d, idx, side, kind, tk, sk, H, mid)
                o["coin"] = c
                sig[f].append(o)
        print(c, {f: sum(len(x) for x in sig[f] if (x.coin == c).any()) for f in FAM}, flush=True)
    out = {}
    for f in FAM:
        S = pd.concat(sig[f]).sort_values(["open"], kind="stable")
        T, bal = simulate(S, 0.0005)
        T.to_csv(HERE / f"trades_{f}.csv", index=False)
        out[f] = report(T, bal)
        T2, bal2 = simulate(S, 0.0002)
        out[f]["report_only_fee_0.02pct"] = {"final": round(bal2, 2), "avg_pct": round(T2.ret.mean() * 100, 3) if len(T2) else None}
        out[f]["signals"] = len(S)
        print(f, json.dumps(out[f]), flush=True)
    (HERE / "result.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
