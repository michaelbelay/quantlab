"""Parity: v4_forward.py's rule code on the research data must reproduce batch_v.py v4((1.5, 7)) trade for trade.

    .venv\Scripts\python.exe research\fresh\forward_v4\parity.py
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
src = (HERE.parent / "batch_v.py").read_text(encoding="utf-8")
__file__ = str(HERE.parent / "batch_v.py")             # batch_v/batch_b resolve their files from __file__
exec(src[:src.index("FAMV = {")])                     # research: D, DV, FE, v4(), FIT0 ...
__file__ = str(HERE / "parity.py")
sys.path.insert(0, str(HERE))
import v4_forward as fw  # noqa: E402

ref = v4((1.5, 7))
ref = ref.assign(t_in=pd.to_datetime(ref.t_in, utc=True)).sort_values(["coin", "t_in"]).reset_index(drop=True)
rows = []
for c in ("BTC", "ETH"):
    x = D[c][["open", "high", "low", "close"]]
    fe = fw.features(x, DV[c])
    rows += fw.run_coin(c, x, D[c]["fund"][D[c]["fund"] != 0], fe, x.index[0])   # same warm-up as research
new = pd.DataFrame(rows)
new = new[new.status == "closed"].assign(t_in=lambda d: pd.to_datetime(d.t_in, utc=True))
new = new[new.t_in >= FIT0]                            # research reports entries from 2022 on
new = new.sort_values(["coin", "t_in"]).reset_index(drop=True)
m = ref.merge(new, on=["coin", "t_in"], how="outer", indicator=True)
both = m[m._merge == "both"]
diff = (both.ret - both.ret_pct).abs()
print(f"research {len(ref)} trades, forward code {len(new)}, matched {len(both)}, "
      f"only research {int((m._merge == 'left_only').sum())}, only forward {int((m._merge == 'right_only').sum())}")
print(f"return diff (pct points): max {diff.max():.6f}, median {diff.median():.6f}")
print(m[m._merge != "both"][["coin", "t_in", "ret", "ret_pct", "_merge"]].to_string())
ok = len(both) == len(ref) == len(new) and diff.max() < 1e-3                 # ret_pct is rounded to 3 decimals
print("PARITY OK" if ok else "PARITY MISMATCH")
sys.exit(0 if ok else 1)
