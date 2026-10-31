"""Out-of-time test, OUT_OF_TIME_2026-10-04.md: SA trend on BTC/ETH/BNB, 2017-08 -> 2020-12 (never used by research)."""
from __future__ import annotations

import io
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE)]
import sim as SM  # noqa: E402

OUT = ROOT / "data" / "market" / "oot"
ARCH = "https://data.binance.vision/data/spot/monthly/klines"


def fetch(sym: str) -> pd.DataFrame:
    p = OUT / f"{sym}_1d.feather"
    if p.exists():
        return pd.read_feather(p)
    parts = []
    for y in range(2017, 2021):
        for m in range(1, 13):
            r = requests.get(f"{ARCH}/{sym}/1d/{sym}-1d-{y}-{m:02d}.zip", timeout=60)
            if r.status_code == 404:
                continue
            r.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                parts.append(pd.read_csv(z.open(z.namelist()[0]), header=None))
    d = pd.concat(parts, ignore_index=True).iloc[:, :8]
    d.columns = ["t", "open", "high", "low", "close", "volume", "ct", "qvol"]
    d = d[pd.to_numeric(d["t"], errors="coerce").notna()]
    d["date"] = pd.to_datetime(pd.to_numeric(d["t"]), unit="ms", utc=True).dt.floor("D")
    d = d[["date", "open", "high", "low", "close", "qvol"]].astype({c: float for c in ("open", "high", "low", "close", "qvol")})
    d = d.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    OUT.mkdir(parents=True, exist_ok=True)
    d.to_feather(p)
    return d


def panel(syms):
    cols = {}
    for s in syms:
        d = fetch(s + "USDT").set_index("date")
        cols[s] = d
    idx = pd.date_range(min(d.index.min() for d in cols.values()), pd.Timestamp("2020-12-31", tz="UTC"), freq="D")
    D = {k: pd.DataFrame({s: cols[s][k].reindex(idx) for s in syms}) for k in ("close", "high", "low", "qvol")}
    D["ret"] = D["close"].pct_change(fill_method=None)
    D["funding"] = D["close"] * 0.0
    return D


def sa(D, coins, long_only, every, lb=20, target=0.40, cap=2.0):
    c = D["close"][coins]
    sig = np.sign(c / c.shift(lb) - 1)
    if long_only:
        sig = sig.clip(lower=0)
    vol = D["ret"][coins].rolling(30, min_periods=20).std() * np.sqrt(365)
    W = (sig * (target / vol)).clip(-cap, cap).where(c.notna(), 0).fillna(0.0)
    if every > 1:
        m = pd.Series(False, index=W.index)
        m.iloc[::every] = True
        W = W.where(m, np.nan).ffill().fillna(0.0)
    return W / len(coins)


def twin(W, rng, long_only):
    """Random timing (long-only) or random direction (long/short), same exposure sizes and holding lengths."""
    out = W.copy() * 0.0
    for col in W.columns:
        w = W[col].to_numpy()
        seg = np.cumsum(np.r_[1, (np.diff(np.sign(w)) != 0)])
        if long_only:
            # shuffle the on/off holding blocks in time, keeping their lengths and sizes
            blocks = [w[seg == k] for k in range(1, seg.max() + 1)]
            order = rng.permutation(len(blocks))
            out[col] = np.concatenate([blocks[i] for i in order])
        else:
            flip = rng.choice([-1.0, 1.0], size=seg.max() + 1)[seg]
            out[col] = np.abs(w) * flip
    return out


def run_one(name, D, coins, long_only, every, minn, rng, reps=200):
    W = sa(D, coins, long_only, every)
    m = SM.metrics(SM.simulate(W, D, minn=minn))
    m2 = SM.metrics(SM.simulate(W, D, minn=minn, cost_mult=2.0))
    finals = np.array([SM.simulate(twin(W, rng, long_only), D, minn=minn)["equity"].iloc[-1] for _ in range(reps)])
    eq = SM.simulate(W, D, minn=minn)["equity"]
    h1 = eq.loc[:"2018-12-31"]
    h2 = eq.loc["2019-01-01":]
    m.pop("daily")
    m.update(pf_2x=m2["pf"], final_2x=m2["final"], random_pct=float((finals < m["final"]).mean() * 100),
             twin_median=float(np.median(finals)),
             half1=float(h1.iloc[-1] / h1.iloc[h1.ne(300).argmax()] - 1) if len(h1) else None,
             half2=float(h2.iloc[-1] / h2.iloc[0] - 1), design=name, coins=coins,
             bh=float(np.mean([D["close"][c].dropna().iloc[-1] / D["close"][c].dropna().iloc[0] - 1 for c in coins])))
    ok = [(m["pf"] or 0) >= 1.10, (m["pf_2x"] or 0) >= 1.05, m["max_dd"] <= 0.50, (m["half1"] or 0) > 0, m["half2"] > 0, m["random_pct"] >= 95]
    m["class"] = "G" if all(ok) else "Y" if (m["final"] > 300 and (m["pf"] or 0) >= 1.10 and m["random_pct"] >= 90) else "O" if m["final"] > 300 else "R"
    return m


def main():
    D = panel(["BTC", "ETH", "BNB"])
    minn = SM.min_notionals()
    rng = np.random.default_rng(2017)
    print(f"out-of-time data: {D['close'].index[0].date()} -> {D['close'].index[-1].date()}; first closes: "
          + ", ".join(f"{c} {D['close'][c].first_valid_index().date()}" for c in D["close"].columns), flush=True)
    rows = []
    for basket in (["BTC", "ETH", "BNB"], ["BTC", "ETH"]):
        for name, lo, ev in (("SA-L", True, 1), ("SA-LS", False, 1), ("SA-L-W", True, 7), ("SA-LS-W", False, 7)):
            m = run_one(name, D, basket, lo, ev, minn, rng)
            rows.append(m)
            print(f"{'/'.join(basket):12} {name:8} 300 -> {m['final']:7.0f} (2x {m['final_2x']:6.0f}) | CAGR {m['cagr']:+.1%} | DD {m['max_dd']:.0%} | "
                  f"PF {m['pf'] or 0:.2f}/{m['pf_2x'] or 0:.2f} | 2017-18 {m['half1']:+.0%} | 2019-20 {m['half2']:+.0%} | trades {m['trades']} | "
                  f"twin p{m['random_pct']:.0f} (median {m['twin_median']:.0f}) | buy&hold avg {m['bh']:+.0%} | {m['class']}", flush=True)
    (HERE / "out_of_time_results.json").write_text(json.dumps({"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                                               "rows": rows}, indent=1, default=float), encoding="utf-8")
    print("OOT_COMPLETE")


if __name__ == "__main__":
    main()
