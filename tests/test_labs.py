"""The bear and scalp labs decide verdicts from a t-statistic. A fixed take-profit used to make it explode.

Guards the 2026-11-13 fix: an idea whose every win pays the same percentage can no longer pass the verdict gate
on arithmetic. cdeep_funding_take reported t = 1713 on 7 trades that were all exactly +4.8%.
"""
import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    except SystemExit:                      # the labs parse argv at import; the functions are still bound
        pass
    return mod


@pytest.fixture(scope="module")
def labs():
    return [load("_bear_lab", "research/bear_lab/bear_lab.py"),
            load("_scalp_lab", "research/scalp_lab/scalp_lab.py")]


def test_a_fixed_take_profit_can_no_longer_fake_a_verdict(labs):
    """5 days that all pay exactly the take-profit: the old formula gave ~548, the gate wants 2.5."""
    take = pd.Series([4.80, 4.80, 4.81, 4.82, 4.80])
    for m in labs:
        t = m.day_t(take)
        assert t < 2.5, f"{m.__name__}: {t}"
        assert t == pytest.approx(1.86, abs=0.01)       # what 5 winning days alone can prove


def test_no_variance_at_all_does_not_divide_by_zero(labs):
    for m in labs:
        assert m.day_t(pd.Series([4.8] * 6)) == pytest.approx(2.15, abs=0.01)   # 6 winning days, p = 1/64
        assert m.day_t(pd.Series([4.8])) == 0.0
        assert m.day_t(pd.Series([], dtype=float)) == 0.0


def test_a_real_run_can_still_pass(labs):
    """12 winning days with genuine spread must stay above the 2.5 gate - the fix must not block real ideas."""
    real = pd.Series([1.0, 2.0, 0.5, 3.0, 1.5, 0.2, 2.2, 1.1, 0.8, 1.9, 2.5, 0.4])
    for m in labs:
        assert m.day_t(real) >= 2.5


def test_a_losing_idea_keeps_a_negative_t(labs):
    for m in labs:
        assert m.day_t(pd.Series([-1.0, 0.5, -2.0, -0.3, -1.1])) < 0


def test_the_cap_only_ever_lowers_the_number(labs):
    """The sign-test bound may never make an idea look stronger than the plain t did."""
    import numpy as np
    rng = np.random.default_rng(20261113)
    for m in labs:
        for _ in range(200):
            d = pd.Series(rng.normal(0.5, 1.0, rng.integers(2, 40)))
            sd = d.std(ddof=1)
            plain = d.mean() / sd * np.sqrt(len(d)) if sd > 0 else float("inf")
            assert m.day_t(d) <= round(plain, 2) + 1e-9


def test_the_verdict_gate_itself_was_not_moved(labs):
    for m in labs:
        assert m.VERDICT["min_t"] == 2.5
