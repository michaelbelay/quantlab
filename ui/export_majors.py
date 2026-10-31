r"""Export MajorsTrend (deployable daily form) equity for the UI:
    .venv\Scripts\python.exe ui\export_majors.py
Writes data/ui_majors_equity.json (read-only use of research/cap300)."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
CAP = Path(__file__).resolve().parents[1] / "research" / "cap300"
sys.path[:0] = [str(CAP), str(CAP.parent / "pipeline")]
import deployable as DP, sim as SM  # noqa: E402

D = DP.panel(); minn = SM.min_notionals(); C = DP.COINS
w = DP.weights(D)
a, b = "2017-08-17", "2026-09-21"
r = SM.simulate(w.loc[a:b], {k: v.loc[a:b] for k, v in D.items()}, minn=minn,
                trade_days=pd.Series(True, index=w.index).loc[a:b])
eq = r["equity"]
btc = D["close"]["BTC"].loc[eq.index[0]:eq.index[-1]]
hold = 300 * btc / btc.iloc[0]
m = SM.metrics(r)
yr = eq.resample("YE").last(); yr = (yr / yr.shift(1).fillna(300) - 1) * 100
out = {"name": "MajorsTrend (long-only, BTC/ETH/BNB, daily, 1x)", "start": a, "end": b,
       "metrics": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items() if k not in ("daily", "folds")},
       "equity": [[int(t.timestamp()), round(float(v), 2)] for t, v in eq.items()],
       "btc_hold": [[int(t.timestamp()), round(float(v), 2)] for t, v in hold.items() if np.isfinite(v)],
       "drawdown": [[int(t.timestamp()), round(float(v), 4)] for t, v in (eq / eq.cummax() - 1).items()],
       "years": {str(t.year): round(float(v), 1) for t, v in yr.items()},
       "exposure": [[int(t.timestamp()), round(float(v), 3)] for t, v in w.loc[a:b].sum(axis=1).items()]}
p = Path(__file__).resolve().parents[1] / "data" / "ui_majors_equity.json"
p.write_text(json.dumps(out), encoding="utf-8")
print("wrote", p, "final", out["metrics"]["final"], "dd", out["metrics"]["max_dd"], out["years"])
