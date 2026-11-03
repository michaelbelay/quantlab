"""Bear batch 10 (O1-O6), open interest shorts. Register: REGISTER_BEAR_OI_2026-11-01.md.

    .venv\\Scripts\\python.exe research\\bear\\bear_oi.py

Output: research/bear/batch10/trades_<idea>.csv, report.json. Nothing here is tuned after the run.
"""
from __future__ import annotations

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

OUT = HERE / "batch10"
OI_DIR = b5.ROOT / "data" / "market" / "oi"
COINS, H, C, N, IDX, NC = b5.COINS, b5.H, b5.C, b5.N, b5.IDX, b6.NC
EL, COST = b6.EL, b5.COST


def hourly(col: str) -> pd.DataFrame:
    """value for each 1h bar = last 5m row with time <= bar open + 55 min."""
    out = {}
    for c in COINS:
        d = pd.read_parquet(OI_DIR / f"{c}.parquet")[col]
        d = d[d.index < b5.bx.END]
        out[c] = d.resample("h", label="left", closed="left").last().reindex(H)
    return pd.DataFrame(out)


def rank_prev(df: pd.DataFrame, n: int = 720) -> pd.DataFrame:
    return df.rolling(n + 1, min_periods=n + 1).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True)


def gap_signal(sig: np.ndarray, gap: int) -> np.ndarray:
    """keep a signal only if the same coin had none in the previous `gap` bars (one per coin per gap)."""
    out = np.zeros_like(sig)
    for k in range(sig.shape[1]):
        last = -10 ** 9
        for i in np.flatnonzero(sig[:, k]):
            if i - last >= gap:
                out[i, k] = True
                last = i
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    oi = hourly("oi_usdt")
    ls = hourly("ls_accounts")
    top = hourly("top_ls_positions")
    bear = np.repeat(b5.BEAR_NEXT[:, None], NC, 1)
    base = bear & EL & oi.notna().to_numpy()
    sma = C.rolling(480, min_periods=480).mean()
    below = (C < sma).to_numpy()
    r24, r72, r7d = (C / C.shift(24) - 1).to_numpy(), (C / C.shift(72) - 1).to_numpy(), (C / C.shift(168) - 1).to_numpy()
    oi24, oi72 = (oi / oi.shift(24) - 1).to_numpy(), (oi / oi.shift(72) - 1).to_numpy()
    R, P = {}, {}

    s = gap_signal(base & below & (r24 >= 0.05) & (oi24 >= 0.10), 24)
    R["O1_leveraged_bounce"], P["O1_leveraged_bounce"] = b6.run_single(s, -1, 0.08, hold=48)

    s = gap_signal(base & (r24 <= -0.03) & (oi24 >= 0.10), 24)
    R["O2_new_shorts_trend"], P["O2_new_shorts_trend"] = b6.run_single(s, -1, 0.06, hold=48)

    lr = rank_prev(ls).to_numpy()
    s = gap_signal(base & below & (lr >= 0.90) & (r7d < 0), 72)
    R["O3_retail_crowded_long"], P["O3_retail_crowded_long"] = b6.run_single(s, -1, 0.08, hold=72)

    tr_ = rank_prev(top).to_numpy()
    s = gap_signal(base & below & (tr_ <= 0.10), 72)
    R["O4_top_traders_short"], P["O4_top_traders_short"] = b6.run_single(s, -1, 0.08, hold=72)

    tot = oi.sum(axis=1, min_count=5)                                    # coins join as they list
    n_live = oi.notna().sum(axis=1)
    tot = tot.where(n_live == n_live.shift(168))                         # 7-day change only when the set is unchanged
    t7 = (tot / tot.shift(168) - 1).to_numpy()
    btc7 = (C["BTC"] / C["BTC"].shift(168) - 1).to_numpy()
    ev = b5.DAILY & b5.BEAR_NEXT & (t7 >= 0.15) & (btc7 <= 0)
    keep, last = np.zeros(N, bool), -10 ** 9
    for i in np.flatnonzero(ev):
        if i - last >= 72:
            keep[i], last = True, i
    R["O5_market_leverage_build"], P["O5_market_leverage_build"] = b6.run_single(np.repeat(keep[:, None], NC, 1) & EL, -1, 0.10, hold=72)

    hi72 = C.rolling(72, min_periods=72).max().to_numpy()
    s = gap_signal(base & (b5.CL >= hi72) & (oi72 <= -0.10), 24)
    R["O6_covering_rally"], P["O6_covering_rally"] = b6.run_single(s, -1, 0.08, hold=48)

    rep = {}
    for k, tr in R.items():
        tr.sort_values("net").to_csv(OUT / f"trades_{k}.csv", index=False)
        rep[k] = bg.stats(tr)
        if rep[k]["verdict"] == "🟠":
            s1, s2 = bg.step2(P[k], N, H, COST, 1), bg.step2(P[k], N, H, COST, 2)
            rep[k]["step2"], rep[k]["step2_2x"] = s1, s2
            rep[k]["verdict"] = "🟡" if (s1["profit_usdt"] > 0 and s2["profit_usdt"] > 0 and s1["max_dd_pct"] >= -35
                                        and s1["worst_trade_usdt"] >= -30) else "🟠"
        print(k, json.dumps(rep[k], ensure_ascii=False))
    (OUT / "report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
