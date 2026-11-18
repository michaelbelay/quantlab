"""The money path: entries, stops, time exits, restarts, a refused stop order, the day-loss switch.

Runs against a fake exchange (no network, no keys). Covers what went wrong on 2026-11-03 (reboot, torn heartbeat,
exits booked a week late) and the live-order risks listed in ASSESSMENT_2026-11-07.md section 6.
"""
import json
import sqlite3

import ccxt
import pandas as pd
import pytest

from trader import broker as br
from trader import engine as en
from trader import fsio
from trader.settings import FEE, SLIPPAGE
from trader.store import Store

T0 = pd.Timestamp("2026-11-01 14:00", tz="UTC")          # the candle the test trades are opened in
H = pd.Timedelta(hours=1)
ms = lambda t: int(t.timestamp() * 1000)                  # noqa: E731


class FakeEx:
    """Just enough of ccxt.binanceusdm. Prices, candles, funding and the account are plain dicts the test fills."""

    def __init__(self):
        self.last, self.k1h, self.k1m, self.fund = {}, {}, {}, {}
        self.pos, self.fills, self.orders, self.refuse = {}, {}, [], set()

    # -- public data
    def fetch_tickers(self, syms):
        return {s: {"last": self.last[s.split("/")[0]]} for s in syms if s.split("/")[0] in self.last}

    def fapiPublicGetKlines(self, p):
        rows = (self.k1h if p["interval"] == "1h" else self.k1m).get(p["symbol"][:-4], [])
        rows = [r for r in rows if ms(r[0]) >= p.get("startTime", 0)][: p["limit"]]
        return [[ms(t), o, h, l, c, 1, 0, 1, 0, 0, 1] for t, o, h, l, c in rows]

    def fapiPublicGetFundingRate(self, p):
        return [{"fundingTime": ms(t), "fundingRate": r, "markPrice": m} for t, r, m in self.fund.get(p["symbol"][:-4], [])]

    # -- account
    def load_markets(self): pass
    def set_margin_mode(self, *a): pass
    def set_leverage(self, *a): pass
    def amount_to_precision(self, sym, x): return f"{x:.6f}"
    def price_to_precision(self, sym, x): return f"{x:.6f}"
    def fetch_balance(self): return {"total": {"USDT": 400.0}}
    def fetch_order(self, oid, sym): return {"average": None}
    def cancel_order(self, oid, sym, params=None): self.orders.append(("cancel", sym, oid))

    def create_order(self, sym, kind, side, amount, price=None, params=None):
        if kind in self.refuse or (kind, bool((params or {}).get("reduceOnly"))) in self.refuse:
            raise ccxt.ExchangeError(f"{kind} refused")
        coin = sym.split("/")[0]
        self.orders.append((kind, sym, side, amount))
        if kind == "market":
            self.pos[sym] = 0.0 if (params or {}).get("reduceOnly") else amount
            return {"id": str(len(self.orders)), "average": self.last[coin], "filled": amount}
        return {"id": f"stop{len(self.orders)}"}

    def fetch_positions(self, syms=None):
        return [{"symbol": s, "contracts": n} for s, n in self.pos.items() if syms is None or s in syms]

    def fetch_my_trades(self, sym, since=None, limit=None):
        return self.fills.get(sym, [])


def flat(coin_px: float, start: pd.Timestamp, hours: int):
    return [(start + i * H, coin_px, coin_px * 1.001, coin_px * 0.999, coin_px) for i in range(hours)]


@pytest.fixture
def rig(tmp_path, monkeypatch):
    said = []
    monkeypatch.setattr(en, "RUNTIME", tmp_path)
    monkeypatch.setattr(en.notify, "send", said.append)
    monkeypatch.setattr(br, "min_cost", lambda coin: 5.0)
    monkeypatch.setattr(br.time, "sleep", lambda s: None)
    ex = FakeEx()

    def make(mode="paper"):
        store = Store(tmp_path / f"{mode}.sqlite", 400.0 if mode == "paper" else None)
        b = br.PaperBroker(ex, store) if mode == "paper" else br.LiveBroker(ex, store)
        return en.Engine(mode, ex=ex, broker=b, store=store)
    return ex, make, said


def signal(monkeypatch, coin="HYPE", short=False, sig24=0.036, close=88.0):
    """Make the hour produce exactly one signal, whatever the candles are."""
    S = pd.DataFrame([{"time": T0 - H, "coin": coin, "short": short, "sig24": sig24, "close": close}])
    monkeypatch.setattr(en, "all_candles", lambda ex, coins, hour: ({}, []))
    monkeypatch.setattr(en.ft, "signals", lambda ind: S)


def open_long(ex, make, monkeypatch, px=88.0, mode="paper", at="2026-11-01 14:00:25"):
    ex.last["HYPE"] = px
    signal(monkeypatch)
    monkeypatch.setattr(en, "utcnow", lambda: at)
    e = make(mode)
    if mode == "live":
        en.set_state("live", "running")                              # a live trader starts paused; the test resumes it
    e.hourly(T0)
    return e


# ------------------------------------------------------------------ paper: costs
def test_paper_entry_pays_slippage_and_sets_the_stop_from_the_fill(rig, monkeypatch):
    ex, make, said = rig
    e = open_long(ex, make, monkeypatch)
    (t,) = e.store.open_trades()
    assert t["open_price"] == pytest.approx(88.0 * (1 + SLIPPAGE))
    assert t["stop_price"] == pytest.approx(t["open_price"] * (1 - 2 * 0.036))
    assert t["fees"] == pytest.approx(t["stake"] * FEE)
    assert "ENTRY HYPE long" in said[-1]


def test_stop_between_price_checks_pays_slippage_and_funding(rig, monkeypatch):
    ex, make, _ = rig
    e = open_long(ex, make, monkeypatch)
    (t,) = e.store.open_trades()
    ex.last["HYPE"] = 80.0                                           # through the stop (81.7)
    ex.k1h["HYPE"] = flat(88.0, T0, 3)
    ex.k1m["HYPE"] = [(T0 + pd.Timedelta(minutes=1), 88.0, 88.1, 87.9, 88.0)]
    ex.fund["HYPE"] = [(T0 + H, 0.0001, 88.0)]                       # one funding stamp while open: the long pays
    e.exits(T0 + 2 * H + pd.Timedelta(minutes=5))
    (c,) = e.store.closed_trades()
    assert c["reason"] == "stop" and c["close_price"] == pytest.approx(80.0 * (1 - SLIPPAGE))
    assert c["funding"] == pytest.approx(0.0001 * 88.0 * t["amount"])
    assert c["pnl"] == pytest.approx((c["close_price"] - t["open_price"]) * t["amount"] - c["fees"] - c["funding"])


# ------------------------------------------------------------------ paper: exits come from candles, not from "now"
def test_downtime_does_not_move_the_exit(rig, monkeypatch):
    """2026-11-03: the trader was down for 8 days. HYPE never touched its stop inside its 48 hours, so the trade is a
    time exit at the open of the 48h candle - not a 'stop' at the price of 8 days later."""
    ex, make, said = rig
    e = open_long(ex, make, monkeypatch)
    due = T0 + 48 * H
    ex.k1h["HYPE"] = flat(88.0, T0, 48) + [(due, 86.3, 87.7, 85.5, 86.9)] + flat(73.0, due + H, 200)
    ex.k1m["HYPE"] = [(T0 + pd.Timedelta(minutes=1), 88.0, 88.1, 87.9, 88.0)]
    ex.last["HYPE"] = 73.1                                           # far below the stop by the time we wake up
    e.audited = None                                                 # = a fresh start
    e.exits(T0 + 10 * 24 * H)
    (c,) = e.store.closed_trades()
    assert c["reason"] == "time_48h" and c["close_time"] == "2026-11-03 14:00:00"
    assert c["close_price"] == pytest.approx(86.3 * (1 - SLIPPAGE))
    assert "rebuilt from candles" in c["note"] and "happened 11-03 14:00" in said[-1]


def test_wick_through_the_stop_inside_a_closed_candle_is_a_stop_at_the_stop(rig, monkeypatch):
    ex, make, _ = rig
    e = open_long(ex, make, monkeypatch)
    (t,) = e.store.open_trades()
    k = flat(88.0, T0, 6)
    k[3] = (T0 + 3 * H, 88.0, 88.2, 80.0, 87.5)                      # wick to 80 and back: 20 s checks never saw it
    ex.k1h["HYPE"], ex.k1m["HYPE"] = k, [(T0 + pd.Timedelta(minutes=1), 88.0, 88.1, 87.9, 88.0)]
    ex.last["HYPE"] = 87.5
    e.audited = None
    e.exits(T0 + 5 * H + pd.Timedelta(seconds=15))
    (c,) = e.store.closed_trades()
    assert c["reason"] == "stop" and c["close_price"] == pytest.approx(t["stop_price"] * (1 - SLIPPAGE))
    assert c["close_time"] == "2026-11-01 18:00:00"


def test_gap_through_the_stop_fills_at_the_open(rig, monkeypatch):
    ex, make, _ = rig
    e = open_long(ex, make, monkeypatch)
    k = flat(88.0, T0, 4)
    k[2] = (T0 + 2 * H, 79.0, 79.5, 78.0, 79.2)                      # opens below the stop
    ex.k1h["HYPE"], ex.k1m["HYPE"] = k, [(T0 + pd.Timedelta(minutes=1), 88.0, 88.1, 87.9, 88.0)]
    ex.last["HYPE"] = 88.0
    e.audited = None
    e.exits(T0 + 3 * H + pd.Timedelta(seconds=15))
    assert e.store.closed_trades()[0]["close_price"] == pytest.approx(79.0 * (1 - SLIPPAGE))


def test_a_low_before_the_entry_in_the_entry_hour_is_not_a_stop(rig, monkeypatch):
    ex, make, _ = rig
    e = open_long(ex, make, monkeypatch, at="2026-11-01 14:45:39")
    k = flat(88.0, T0, 3)
    k[0] = (T0, 80.0, 88.5, 79.0, 88.0)                              # the hour's low (79) was at 14:10, before the entry
    ex.k1h["HYPE"] = k
    ex.k1m["HYPE"] = [(T0 + pd.Timedelta(minutes=m), 88.0, 88.2, 87.8, 88.0) for m in range(46, 60)]
    e.audited = None
    e.exits(T0 + 2 * H + pd.Timedelta(seconds=15))
    assert len(e.store.open_trades()) == 1


# ------------------------------------------------------------------ entries
def test_a_late_start_reads_the_signal_but_does_not_enter(rig, monkeypatch):
    ex, make, _ = rig
    ex.last["HYPE"] = 88.0
    signal(monkeypatch)
    e = make()
    e.hourly(T0, fresh=False)
    assert e.store.open_trades() == []
    e.hourly(T0, fresh=True)
    assert len(e.store.open_trades()) == 1


def test_a_failed_hour_is_tried_again_while_the_signal_is_fresh(rig, monkeypatch):
    ex, make, _ = rig
    e = make()
    calls = []

    def boom(hour, fresh=True):
        calls.append(fresh)
        if len(calls) == 1:
            raise ccxt.NetworkError("down")
    monkeypatch.setattr(e, "hourly", boom)
    monkeypatch.setattr(e, "exits", lambda now: None)
    monkeypatch.setattr(en, "datetime", type("D", (), {"now": staticmethod(lambda tz=None: (T0 + pd.Timedelta(seconds=15)).to_pydatetime())}))
    with pytest.raises(ccxt.NetworkError):
        e.tick()
    assert e.last_hour is None
    e.tick()
    assert calls == [True, True] and e.last_hour == T0


def test_day_loss_switch_halts_entries_until_resume(rig, monkeypatch):
    ex, make, said = rig
    e = open_long(ex, make, monkeypatch)
    ex.last["HYPE"] = 30.0                                           # the open trade is deep under water: > 6% of the wallet
    signal(monkeypatch, coin="NEAR", short=True, close=4.1)
    ex.last["NEAR"] = 4.1
    e.hourly(T0)
    assert [t["coin"] for t in e.store.open_trades()] == ["HYPE"]
    until = json.loads((en.RUNTIME / "paper_state.json").read_text())["halt_until"]
    assert until == (pd.Timestamp.now(tz="UTC").floor("D") + pd.Timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    assert any("DAY-LOSS HALT" in m for m in said)
    monkeypatch.setattr(en, "utcnow", lambda: "2000-01-01 00:00:00")
    assert en.get_state("paper") == "halted"
    monkeypatch.setattr(en, "utcnow", lambda: until)
    assert en.get_state("paper") == "running"                        # lifts itself at the next UTC day
    monkeypatch.setattr(en, "utcnow", lambda: "2000-01-01 00:00:00")
    en.set_state("paper", "running")
    assert en.get_state("paper") == "running"                        # ... or by hand


# ------------------------------------------------------------------ live orders
def test_live_entry_puts_the_exchange_stop_at_the_stop_of_the_real_fill(rig, monkeypatch):
    ex, make, _ = rig
    e = open_long(ex, make, monkeypatch, mode="live")
    (t,) = e.store.open_trades()
    assert [o[0] for o in ex.orders] == ["market", "STOP_MARKET"]
    assert t["stop_order_id"] == "stop2" and t["stop_price"] == pytest.approx(88.0 * (1 - 2 * 0.036))


def test_refused_stop_order_closes_the_position_again(rig, monkeypatch):
    """The orphan case: entry filled, stop refused. Nothing may stay open without a stop and without a record."""
    ex, make, said = rig
    ex.refuse.add("STOP_MARKET")
    e = open_long(ex, make, monkeypatch, mode="live")
    assert e.store.open_trades() == [] and ex.pos["HYPE/USDT:USDT"] == 0.0
    assert any("ENTRY ABORTED" in m for m in said)


def test_refused_stop_and_refused_close_is_recorded_and_guarded_by_price(rig, monkeypatch):
    ex, make, said = rig
    ex.refuse |= {"STOP_MARKET", ("market", True)}
    e = open_long(ex, make, monkeypatch, mode="live")
    (t,) = e.store.open_trades()
    assert t["stop_order_id"] is None and "NO EXCHANGE STOP" in t["note"] and any("WARNING HYPE" in m for m in said)
    ex.refuse.clear()
    ex.last["HYPE"] = 80.0                                           # beyond the stop, position still there
    e.exits(T0 + H)
    assert len(e.store.open_trades()) == 1                           # first sighting: wait one more check
    e.exits(T0 + H)
    (c,) = e.store.closed_trades()
    assert c["reason"] == "stop_soft" and ex.pos["HYPE/USDT:USDT"] == 0.0


def test_position_gone_at_the_stop_is_a_stop_and_elsewhere_is_external(rig, monkeypatch):
    ex, make, said = rig
    e = open_long(ex, make, monkeypatch, mode="live")
    (t,) = e.store.open_trades()
    ex.pos["HYPE/USDT:USDT"] = 0.0
    ex.fills["HYPE/USDT:USDT"] = [{"side": "sell", "price": t["stop_price"] * 0.999, "amount": t["amount"]}]
    e.exits(T0 + H)
    assert e.store.closed_trades()[0]["reason"] == "stop"

    e2 = open_long(ex, make, monkeypatch, mode="live", at="2026-11-01 16:00:25")
    t2 = e2.store.open_trades()[0]
    ex.pos["HYPE/USDT:USDT"] = 0.0
    ex.fills["HYPE/USDT:USDT"] = [{"side": "sell", "price": 95.0, "amount": t2["amount"]}]      # closed by hand in profit
    e2.exits(T0 + 3 * H)
    assert e2.store.closed_trades()[-1]["reason"] == "external" and any("outside the trader" in m for m in said)


def test_no_entry_in_a_coin_the_account_already_holds(rig, monkeypatch):
    ex, make, said = rig
    ex.pos["HYPE/USDT:USDT"] = 2.0                                   # Michael's own trade, or an entry whose record was lost
    e = open_long(ex, make, monkeypatch, mode="live")
    assert e.store.open_trades() == [] and ex.orders == []
    assert any("not in the trader's book" in m for m in said)


# ------------------------------------------------------------------ files
def test_damaged_heartbeat_reads_as_unknown_not_as_a_crash(tmp_path):
    hb = tmp_path / "paper_heartbeat.txt"
    hb.write_bytes(b"\x00" * 19)                                     # what the 2026-11-03 reboot left behind
    assert fsio.read_time(hb) is None and fsio.age_min(hb) is None
    fsio.write_atomic(hb, "2026-11-12 19:00:00")
    assert fsio.read_time(hb) == pd.Timestamp("2026-11-12 19:00", tz="UTC").to_pydatetime()
    assert not hb.with_name(hb.name + ".tmp").exists()


def test_an_old_database_gets_the_new_columns_and_keeps_its_rows(tmp_path):
    db = tmp_path / "paper.sqlite"
    with sqlite3.connect(db) as c:
        c.executescript("""CREATE TABLE trades (id INTEGER PRIMARY KEY AUTOINCREMENT, coin TEXT NOT NULL, short INTEGER NOT NULL,
            signal_time TEXT NOT NULL, sig24 REAL NOT NULL, open_time TEXT NOT NULL, open_price REAL NOT NULL, amount REAL NOT NULL,
            stake REAL NOT NULL, stop_price REAL NOT NULL, stop_order_id TEXT, close_time TEXT, close_price REAL, reason TEXT,
            fees REAL NOT NULL DEFAULT 0, pnl REAL);
            INSERT INTO trades (coin, short, signal_time, sig24, open_time, open_price, amount, stake, stop_price)
            VALUES ('BNB', 1, 's', 0.02, '2026-11-12 19:00:32', 654.94, 0.1, 65.6, 684.39);""")
    s = Store(db, 400.0)
    (t,) = s.open_trades()
    assert t["coin"] == "BNB" and t["funding"] == 0 and t["note"] is None


def test_repair_moves_a_late_exit_back_and_keeps_the_old_values_in_the_note(rig, monkeypatch):
    """Trade 4 of the real paper book: HYPE long, booked on 2026-11-11 as a stop at 73.108 (-11.37)."""
    from trader import repair
    ex, make, _ = rig
    e = make()
    tid = e.store.add(coin="HYPE", short=0, signal_time="s", sig24=0.036, open_time="2026-11-01 14:45:39",
                      open_price=88.063, amount=0.756, stake=66.575, stop_price=81.716, stop_order_id=None, fees=0.0333)
    e.store.close(tid, 73.108, "stop", 0.0609, -11.37, when="2026-11-11 19:55:05")
    due = T0 + 48 * H
    ex.k1h["HYPE"] = flat(88.0, T0, 48) + [(due, 86.304, 87.7, 85.5, 86.9)] + flat(73.0, due + H, 300)
    ex.k1m["HYPE"] = [(T0 + pd.Timedelta(minutes=m), 88.0, 88.2, 87.8, 88.0) for m in range(46, 60)]
    (f,) = repair.find(e.store, e.broker)
    assert (f["reason"], f["price"], f["when"]) == ("time_48h", 86.304, "2026-11-03 14:00:00")
    assert f["pnl"] == pytest.approx((86.304 - 88.063) * 0.756 - 66.575 * FEE - 0.756 * 86.304 * FEE)
    monkeypatch.setattr(repair, "Store", lambda *a: e.store)
    monkeypatch.setattr(repair, "exchange", lambda: ex)
    assert repair.main("paper", apply=True) == 0
    (c,) = e.store.closed_trades()
    assert c["reason"] == "time_48h" and c["close_time"] == "2026-11-03 14:00:00" and "was stop at 73.108" in c["note"]
    assert repair.find(e.store, e.broker) == []                       # a second run changes nothing
