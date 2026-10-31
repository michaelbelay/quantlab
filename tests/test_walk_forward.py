import pandas as pd

from quant.eval_c import WALK_FORWARD, walk_forward


def _trades(rets_by_period):
    rows = []
    for (name, a, b), r in zip(WALK_FORWARD["1h"][0], rets_by_period):
        rows.append({"entry_t": pd.Timestamp(a, tz="UTC") + pd.Timedelta(days=1), "ret": r})
    return pd.DataFrame(rows)


def test_needs_5_of_8_on_1h():
    assert walk_forward(_trades([0.01] * 5 + [-0.01] * 3), "1h")["passed"]
    assert not walk_forward(_trades([0.01] * 4 + [-0.01] * 4), "1h")["passed"]


def test_no_window_reaches_spent_period():
    for periods, _ in WALK_FORWARD.values():
        assert max(b for _, _, b in periods) <= "2026-03-26"


def test_trades_after_cutoff_ignored():
    t = pd.DataFrame({"entry_t": [pd.Timestamp("2026-05-01", tz="UTC")], "ret": [1.0]})
    assert walk_forward(t, "1h")["positive"] == 0
