import numpy as np

from strategies.families import band_pick


def test_band_keeps_existing_positions_inside_2k_and_stays_equal():
    s = np.arange(10, dtype=float)                 # 0 = best long ... 9 = best short
    ok = np.ones(10, bool)
    q = np.zeros(10)
    q[3] = 1.0                                     # current long ranked 4th: inside 2k=4 -> kept
    q[6] = -1.0                                    # current short ranked 4th from top: kept
    longs, shorts = band_pick(s, s, ok, ok, 2, q)
    assert set(longs) == {0, 3} and set(shorts) == {9, 6}
    assert len(longs) == len(shorts) and not set(longs) & set(shorts)


def test_band_drops_positions_outside_2k():
    s = np.arange(10, dtype=float)
    ok = np.ones(10, bool)
    q = np.zeros(10)
    q[5] = 1.0                                     # ranked 6th as a long: outside 2k=4 -> replaced
    longs, shorts = band_pick(s, s, ok, ok, 2, q)
    assert set(longs) == {0, 1}


def test_band_equal_counts_when_one_side_is_short_of_candidates():
    s = np.arange(10, dtype=float)
    ok = np.ones(10, bool)
    short_ok = np.zeros(10, bool)
    short_ok[9] = True                             # only one short candidate
    longs, shorts = band_pick(s, s, ok, short_ok, 3, None)
    assert len(longs) == len(shorts) == 1
