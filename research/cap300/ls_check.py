"""MAJORS-TREND long-only (live) vs long/short (SA-LS, validated out-of-time 2017-20), deployable daily form.
Frozen rule, nothing tuned: sign of 20-day return, 40% vol target, cap 2, one third each, 1x gross cap.
Added 2026-10-06: SA-LS was never run as a continuous 2017-26 account. Diagnostic, no selection on 2021-26."""
import numpy as np, pandas as pd
import deployable as DP, sim as SM

D = DP.panel(); minn = SM.min_notionals(); C = DP.COINS
c = D["close"][C]; ret = c / c.shift(20) - 1
vol = D["ret"][C].rolling(30, min_periods=20).std() * np.sqrt(365)
base = ((0.40 / vol).clip(upper=2.0) / 3)
def capped(w): return w.div(np.maximum(w.abs().sum(axis=1), 1.0), axis=0).fillna(0.0)
W = {"LONG-ONLY (live)": capped(base.where(ret > 0, 0.0)),
     "LONG/SHORT": capped(base * np.sign(ret).fillna(0.0))}
mask = pd.Series(True, index=c.index)
for label, a, b in (("OUT-OF-TIME 2017-08 -> 2020-12", "2017-08-17", "2020-12-31"), ("FULL 2017-08 -> 2026-09", "2017-08-17", "2026-09-21"),
                    ("2021-01 -> 2026-09", "2021-01-01", "2026-09-21"), ("RECENT 2026-03-26 -> 09-21", "2026-03-26", "2026-09-21")):
    print(f"\n{label}")
    for k, w in W.items():
        m, m2 = DP.run(D, w, mask, a, b, minn)
        e = SM.simulate(w.loc[a:b], {x: v.loc[a:b] for x, v in D.items()}, minn=minn, trade_days=mask.loc[a:b])["equity"]
        yr = e.resample("YE").last(); yr = (yr / yr.shift(1).fillna(300) - 1) * 100
        ys = " ".join(f"{d.year}:{v:+.0f}%" for d, v in yr.items()) if label.startswith("FULL") else ""
        print(f"  {k:17s} 300 -> {m['final']:7.0f} (2x {m2['final']:7.0f}) CAGR {m['cagr']:+.1%} DD {m['max_dd']:.0%} "
              f"PF {m['pf'] or 0:.2f} Sharpe {m['sharpe']:.2f} trades {m['trades']}  {ys}")
