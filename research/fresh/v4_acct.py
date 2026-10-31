from pathlib import Path
import numpy as np, pandas as pd
src = (Path(__file__).parent / "batch_v.py").read_text(encoding="utf-8")
exec(src[:src.index("FAMV = {")])
f = v4((1.5, 7))
print("distinct signal days:", f.t.dt.normalize().nunique(), "of", len(f), "trades; test days:", f[f.t >= FIT1].t.dt.normalize().nunique())
for lev in (1, 2, 3):
    g = f.copy(); g["ret"] = g.ret * lev
    for lab, h in (("2022-24", g[g.t < FIT1]), ("2025-26", g[g.t >= FIT1]), ("2022-26", g)):
        eq, dd = book(h, 2); print(f"  {lev}x {lab}: 300 -> {eq:.0f}, max drop {dd*100:.0f}%")
print(f[f.t >= FIT1][["coin", "t", "ret"]].to_string())
