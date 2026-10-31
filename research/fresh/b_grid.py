"""All grid settings of B8 and B3 (and B0) on test - robustness of the leads (2026-10-13)."""
from pathlib import Path
src = (Path(__file__).parent / "batch_b.py").read_text(encoding="utf-8")
exec(src[:src.index("res, chosen = {}, {}")])
for name in ("B8 BTC trend alt beta", "B3 rip in downtrend"):
    fn, grid = FAM[name]
    print(name)
    for p in grid:
        f = frame(fn(p)); fi, te = f[f.t < FIT1], f[f.t >= FIT1]
        pf = te.ret[te.ret > 0].sum() / max(1e-9, -te.ret[te.ret < 0].sum())
        print(f"  {str(p):16} fit n {len(fi):4} {fi.ret.mean():+.2f}% | test n {len(te):4} {te.ret.mean():+.2f}% PF {pf:5.2f} "
              f"2025 {te[te.t.dt.year==2025].ret.sum():+5.0f} 2026 {te[te.t.dt.year==2026].ret.sum():+5.0f} | "
              f"2022 {fi[fi.t.dt.year==2022].ret.sum():+5.0f} 2023 {fi[fi.t.dt.year==2023].ret.sum():+5.0f} 2024 {fi[fi.t.dt.year==2024].ret.sum():+5.0f}", flush=True)
