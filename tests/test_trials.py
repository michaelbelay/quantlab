import numpy as np

from quant.trials import _norm_spec, expected_max_t, n_eff


def test_n_eff_independent_vs_identical():
    rng = np.random.default_rng(0)
    x = rng.normal(size=(2000, 10))
    assert 9 < n_eff(x) <= 10
    same = np.repeat(x[:, :1], 10, axis=1)
    assert abs(n_eff(same) - 1) < 1e-6


def test_expected_max_t_matches_literature():
    # Bailey & Lopez de Prado approximation; also used in the 2026-10-09 assessment (N=32 -> ~1.9..2.1)
    assert 1.8 < expected_max_t(32) < 2.2
    assert expected_max_t(1) == 0.0
    assert expected_max_t(10000) > expected_max_t(100)


def test_btc_regime_is_noop_under_both():
    a = {"family": "x", "filters": ["btc_regime", "volume"], "trend_mode": "both"}
    b = {"family": "x", "filters": ["volume"], "trend_mode": "both"}
    c = {"family": "x", "filters": ["btc_regime", "volume"], "trend_mode": "with"}
    assert _norm_spec(a) == _norm_spec(b)
    assert _norm_spec(a) != _norm_spec(c)
