r"""C39 = C32 (funding-crowding fade, unchanged) + ONE filter: market-wide OI fell > 3% over the signal bar.

    .venv\Scripts\python.exe -m quant.run_c39

Dev 2021-01-01 -> 2024-06-30 and validation 2024-07-01 -> 2026-03-31, 1h, all 413 coins, 300 USDT book,
fee 0.05% + slippage 0.05% per side, funding, next-bar entry. Random-timing twins (100) on both windows:
same coin, side and holding length per trade, entry bar drawn uniformly within the window.
Fixed decision rule: SHIP if validation PF > 1.05 AND beats random twins (>= 95th percentile), else KILL.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from strategies.families_c import c14_like

from . import trades as T
from .bars import bars, universe_1h
from .book import metrics, replay
from .eval_c import mins
from .paths import DATA, RUNS

WINDOWS = {"Dev": ("2021-01-01", "2024-07-01"), "Validation": ("2024-07-01", "2026-04-01")}
REPS, OI_DROP = 100, -0.03


def main() -> int:
    chg = pd.read_parquet(DATA / "mkt_oi_1h.parquet")["mkt_oi_chg_1h"]
    rng = np.random.default_rng(39)
    rows, twin = [], {w: np.zeros(REPS) for w in WINDOWS}
    for coin in universe_1h():
        df = bars(coin, "1h")
        if len(df) < 40 * 24:
            continue
        a = T.atr(df)
        ctx = {"bpd": 24, "tf": "1h"}
        _, ss, ex = c14_like(df, a, ctx, 2.5)                              # C32, unchanged
        g = chg.reindex(pd.DatetimeIndex(df["date"])).to_numpy()
        gate = np.isfinite(g) & (g < OI_DROP)                              # missing OI -> no signal
        tr = T.simulate(df, np.zeros_like(ss), ss & gate, ex, a, 24)
        o, c = df["open"].to_numpy(), df["close"].to_numpy()
        d = df["date"]
        for w, (s0, s1) in WINDOWS.items():
            lo = int(d.searchsorted(pd.Timestamp(s0, tz="UTC")))
            hi = int(d.searchsorted(pd.Timestamp(s1, tz="UTC"))) - 1
            wt = [t for t in tr if lo <= t["entry_i"] <= hi]
            for t in wt:
                b = t["bars"]
                if hi - b + 1 <= lo:
                    continue
                e = lo + (rng.random(REPS) * (hi - b + 1 - lo)).astype(int)
                x = np.minimum(e + b - 1, len(c) - 1)
                with np.errstate(invalid="ignore", divide="ignore"):
                    twin[w] += np.nan_to_num(t["side"] * (c[x] / o[e] - 1) - 2 * (T.FEE + T.SLIP))
        for t in tr:
            t["coin"] = coin
            rows.append({k: t[k] for k in ("coin", "side", "entry_t", "exit_t", "ret", "mae", "reason")})
    allt = pd.DataFrame(rows)
    for col in ("entry_t", "exit_t"):
        allt[col] = pd.to_datetime(allt[col], utc=True)
    mn = mins()
    out = {}
    for w, (s0, s1) in WINDOWS.items():
        t = allt[(allt["entry_t"] >= pd.Timestamp(s0, tz="UTC")) & (allt["entry_t"] < pd.Timestamp(s1, tz="UTC"))]
        t = t.reset_index(drop=True)
        if len(t):
            bt, curve = replay(t, mn)
            m = metrics(bt, curve, [])
        else:
            m = {"trades": 0}
        actual = float(t["ret"].sum()) if len(t) else 0.0
        pct = float((twin[w] < actual).mean() * 100) if len(t) else None
        out[w] = {"signals": int(len(t)), "book": m, "twin_pct": pct, "twin_median_sum": float(np.median(twin[w])),
                  "actual_sum": actual}
    v = out["Validation"]
    ship = bool(v["book"].get("trades", 0) and v["book"]["pf"] > 1.05 and (v["twin_pct"] or 0) >= 95)
    out["decision"] = "SHIP" if ship else "KILL"
    (RUNS / "C39_oi_gate.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("| Run | Window | Trades | PF (after costs) | Max DD | Win rate | Beat random twins? |")
    print("|---|---|---|---|---|---|---|")
    for w, (s0, s1) in WINDOWS.items():
        m, r = out[w]["book"], out[w]
        end = (pd.Timestamp(s1) - pd.Timedelta(days=1)).date()
        tw = "n/a (0 trades)" if r["twin_pct"] is None else f"{'Yes' if r['twin_pct'] >= 95 else 'No'} (p{r['twin_pct']:.0f})"
        print(f"| C32 + OI gate · {w} | {s0} → {end} | {m.get('trades', 0)} | {m.get('pf', 'n/a')} | "
              f"{str(m.get('max_dd_pct', 'n/a')) + '%' if m.get('trades') else 'n/a'} | "
              f"{str(m.get('win_rate', 'n/a')) + '%' if m.get('trades') else 'n/a'} | {tw} |")
    print(f"| Random-timing twins | both | 100 replicas per window | — | — | — | Dev p{out['Dev']['twin_pct']}, Validation p{v['twin_pct']} |")
    print(f"\nDECISION: {out['decision']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
