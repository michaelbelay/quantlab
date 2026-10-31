import numpy as np
import pandas as pd

from quant import trades as T
from quant.book import replay


def frame(close, high=None, low=None, n_pre=40):
    close = np.r_[np.full(n_pre, 100.0), np.asarray(close, float)]
    high = close + 0.1 if high is None else np.r_[np.full(n_pre, 100.1), high]
    low = close - 0.1 if low is None else np.r_[np.full(n_pre, 99.9), low]
    d = pd.date_range("2024-01-01", periods=len(close), freq="1D", tz="UTC")
    return pd.DataFrame({"date": d, "open": close, "high": high, "low": low, "close": close,
                         "qvol": 1e9, "fund": 0.0, "volume": 1.0, "taker_buy": np.nan})


def test_entry_is_next_open_and_stop_first_when_both_hit():
    df = frame([100, 100, 100, 100], high=[100.1, 100.1, 120, 100.1], low=[99.9, 99.9, 80, 99.9])
    s = np.zeros(len(df), bool)
    s[40] = True                                     # signal on bar 40 close -> entry bar 41 open
    a = np.full(len(df), 5.0)
    tr = T.simulate(df, s, np.zeros_like(s), T.Exit(stop_atr=2, tp_atr=2, max_hold=10), a, bars_per_day=1)
    assert tr[0]["entry_i"] == 41 and tr[0]["reason"] == "stop"          # bar 42 hits both: stop wins
    assert abs(tr[0]["gross"] - (90 * (1 - T.STOP_EXTRA) / 100 - 1)) < 1e-9


def test_gap_through_stop_fills_at_open():
    close = [100, 100, 70, 70]
    df = frame(close, high=[100.1, 100.1, 70.1, 70.1], low=[99.9, 99.9, 69.9, 69.9])
    s = np.zeros(len(df), bool)
    s[40] = True
    tr = T.simulate(df, s, np.zeros_like(s), T.Exit(stop_atr=2, tp_atr=None, max_hold=10), np.full(len(df), 5.0), 1)
    assert abs(tr[0]["gross"] - (70 * (1 - T.STOP_EXTRA) / 100 - 1)) < 1e-9


def test_short_pays_negative_funding_and_costs():
    df = frame([100, 100, 100])
    df["fund"] = 0.0
    df.loc[42, "fund"] = -0.001                        # negative rate: shorts pay
    s = np.zeros(len(df), bool)
    s[40] = True
    tr = T.simulate(df, np.zeros_like(s), s, T.Exit(stop_atr=50, tp_atr=None, max_hold=3), np.full(len(df), 1.0), 1)
    assert abs(tr[0]["ret"] - (0 - 2 * (T.FEE + T.SLIP) - 0.001)) < 1e-12


def test_book_respects_slots_and_same_direction_cap():
    t0 = pd.Timestamp("2024-01-01", tz="UTC")
    rows = [{"coin": f"C{i}", "side": 1, "entry_t": t0, "exit_t": t0 + pd.Timedelta(days=1), "ret": 0.01,
             "mae": -0.01, "reason": "tp"} for i in range(5)]
    t, curve = replay(pd.DataFrame(rows), {}, slots=20, max_same=3)
    assert t["taken"].sum() == 3
    assert abs(curve.iloc[-1] - (300 + 3 * 15 * 0.01)) < 1e-9
