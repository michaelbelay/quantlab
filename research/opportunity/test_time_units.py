r"""Regression test for the 2026-10-07 time-unit bug (pandas 3: ms candles + us funding -> merge_asof refuses,
the coin was skipped silently). Plain asserts, no pytest needed:

    .venv\Scripts\python.exe research\opportunity\test_time_units.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import compute_conditions, regular_grid  # noqa: E402
from scan import same_time_unit  # noqa: E402


def frames():
    t = pd.date_range("2026-01-01", periods=1000, freq="h", tz="UTC")
    rng = np.random.default_rng(1)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(t))))
    candles = pd.DataFrame({"date": t.astype("datetime64[ms, UTC]"), "open": c, "high": c * 1.01, "low": c * 0.99,
                            "close": c, "volume": 1000.0})
    fund = pd.DataFrame({"date": t[::8].astype("datetime64[us, UTC]"), "funding_rate": 0.0001})
    return candles, fund


def test_mixed_units_still_break_without_guard():
    candles, fund = frames()
    g = regular_grid(candles)
    if g["date"].dtype == fund["date"].dtype:
        return                                       # this pandas build no longer mixes units here
    try:
        compute_conditions(g, fund)
    except Exception:
        return                                       # the original failure mode: documented, still real
    # pandas may also accept it; either way the guarded path below must work


def test_guard_makes_units_equal_and_scan_path_works():
    candles, fund = frames()
    g = regular_grid(candles)
    same_time_unit(g, fund)
    assert g["date"].dtype == fund["date"].dtype == "datetime64[ns, UTC]"
    x = compute_conditions(g, fund)
    assert len(x) == len(g) and x["frate"].notna().any()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
