import numpy as np

from quant import sim
from quant.panel import Panel


def make(T=40, N=4, drift=None, fund=0.0, spike=None):
    close = np.ones((T, N)) * 100.0
    if drift is not None:
        close = close * np.cumprod(np.ones((T, N)) * (1 + np.asarray(drift)), axis=0)
    high, low = close * 1.001, close * 0.999
    if spike is not None:
        t, j, h = spike
        high[t, j] = h
    return Panel(np.arange(T, dtype=np.int64) * 8 * 3600 * 10**9, [f"C{i}" for i in range(N)], close, high, low,
                 np.full((T, N), 1e9), np.full((T, N), fund), np.full(N, 5.0))


def score_index(p, t):
    return np.arange(p.close.shape[1], dtype=float)     # coin 0 long ... coin N-1 short


def test_flat_prices_only_lose_fees():
    sim.MIN_HISTORY = 3
    r = sim.run(make(), score_index, k=1, every=1000)
    # one rebalance: 2 positions x 150 notional x 0.1% = 0.30
    assert abs(r.equity[-1] - (300 - 0.30)) < 1e-6
    assert r.trades == 2


def test_market_move_cancels_out():
    sim.MIN_HISTORY = 3
    r = sim.run(make(drift=[0.01] * 4), score_index, k=1, every=1000)
    assert abs(r.equity[-1] - (300 - 0.30)) < 1e-3       # long and short move together: neutral


def test_short_collects_positive_funding_long_pays():
    sim.MIN_HISTORY = 3
    r = sim.run(make(fund=0.001), score_index, k=1, every=1000)
    assert abs(r.funding) < 1e-9                            # equal notional: paid == received


def test_short_liquidated_on_spike_loses_margin():
    sim.MIN_HISTORY = 3
    p = make(spike=(10, 3, 100 * 1.25))                     # +25% wick on the short coin
    r = sim.run(p, score_index, k=1, every=1000, lev=5.0)   # 5x: liquidation at +19%
    assert r.liquidations == 1
    # each side 300*5/2 = 750 notional, margin 150 lost on the short; fees 1500*0.1% = 1.5
    assert abs(r.equity[-1] - (300 - 1.5 - 150)) < 1e-6


def test_no_liquidation_at_1x_on_same_spike():
    sim.MIN_HISTORY = 3
    r = sim.run(make(spike=(10, 3, 125.0)), score_index, k=1, every=1000, lev=1.0)
    assert r.liquidations == 0


def test_stop_fires_before_liquidation_and_book_stays_equal():
    sim.MIN_HISTORY = 3
    p = make(T=60, spike=(10, 3, 100 * 1.40))              # +40% wick on the short coin
    r = sim.run(p, score_index, k=1, every=1000, lev=2.0, stop=0.30)   # 2x liquidation at +49%
    assert r.liquidations == 0 and r.stops == 1
    # forced rebalance next bar: both sides filled again, equal counts every time
    assert all(len(a) == len(b) == 1 for _, a, b in r.held)
    assert len(r.held) == 2
