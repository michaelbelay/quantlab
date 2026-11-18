"""The trading loop. Every 20 s: stops, 48h exits. Once per hour (10 s after the candle closes): FlowTrend signals, entries.

State file data/trader/<mode>_state.json: "running" (new entries) or "paused" (manages open trades only).
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

import pandas as pd

from . import flowtrend as ft
from . import notify, vault
from .broker import EntryAborted, LiveBroker, PaperBroker
from .fsio import age_min, write_atomic
from .market import all_candles, exchange, funding_paid, last_prices
from .settings import COINS, DAY_LOSS_HALT, ENTRY_GRACE_S, FEE, LEVERAGE, PAPER_WALLET, RUNTIME, SLOTS
from .store import Store, utcnow

log = logging.getLogger("trader")
FMT = "%Y-%m-%d %H:%M:%S"


def state_file(mode: str):
    return RUNTIME / f"{mode}_state.json"


def read_state(mode: str) -> dict:
    try:
        return json.loads(state_file(mode).read_text())
    except Exception:
        return {"state": "paused"}                        # unknown -> safest


def get_state(mode: str) -> str:
    """running | paused | halted. halted = running, but the day-loss switch blocks new entries until halt_until."""
    st = read_state(mode)
    if st.get("state") == "running" and st.get("halt_until") and utcnow() < st["halt_until"]:
        return "halted"
    return st.get("state", "paused")


def set_state(mode: str, state: str) -> None:
    """Pause / resume by hand. Also clears a day-loss halt."""
    RUNTIME.mkdir(parents=True, exist_ok=True)
    write_atomic(state_file(mode), json.dumps({"state": state, "since_utc": utcnow()}))


def halt(mode: str, until: str, why: str) -> None:
    st = read_state(mode)
    st.update(halt_until=until, halt_why=why)
    write_atomic(state_file(mode), json.dumps(st))


def pnl(t: dict, price: float, fees: float) -> float:
    move = (t["open_price"] - price) if t["short"] else (price - t["open_price"])
    return move * t["amount"] - fees


class Engine:
    def __init__(self, mode: str, ex=None, broker=None, store: Store | None = None):
        """ex / broker / store are only passed by the tests; a normal start builds them from the mode."""
        self.mode = mode
        self.tag = "[PAPER] " if mode == "paper" else ""
        self.store = store or Store(RUNTIME / f"{mode}.sqlite", PAPER_WALLET if mode == "paper" else None)
        if broker is not None:
            self.ex, self.broker = ex, broker
        elif mode == "live":
            keys = vault.get("binance")
            if not keys:
                raise SystemExit("no Binance key saved - run: python -m trader.vault set binance")
            self.ex = exchange(keys)
            self.broker = LiveBroker(self.ex, self.store)
        else:
            self.ex = exchange()
            self.broker = PaperBroker(self.ex, self.store)
        self.last_hour: pd.Timestamp | None = None
        self.audited: pd.Timestamp | None = None
        if not state_file(mode).exists():
            set_state(mode, "running" if mode == "paper" else "paused")

    def _say(self, msg: str, level: int = logging.INFO) -> None:
        log.log(level, msg)
        notify.send(msg)

    # ------------------------------------------------------------------ exits
    def _funding(self, t: dict, end: pd.Timestamp) -> float:
        try:
            return funding_paid(self.ex, t["coin"], bool(t["short"]), t["amount"], pd.Timestamp(t["open_time"], tz="UTC"),
                                end, t["open_price"])
        except Exception as e:  # noqa: BLE001 - an exit is never held up by the funding lookup
            log.warning("funding of %s not read (%s) - booked as 0", t["coin"], type(e).__name__)
            return 0.0

    def _close(self, t: dict, reason: str, price: float | None = None, when: pd.Timestamp | None = None) -> None:
        """when: the time the exit really happened if that is not now (paper exits rebuilt from candles)."""
        now = pd.Timestamp(datetime.now(timezone.utc))
        gone = self.broker.live and reason in ("stop", "external")       # Binance already closed the position
        r = {"price": price, "fees": t["amount"] * price * FEE} if gone else self.broker.close(t, reason, price)
        fund = self._funding(t, when or now)
        fees = (t["fees"] or 0) + r["fees"]
        p = pnl(t, r["price"], fees) - fund
        late = when is not None and now - when > pd.Timedelta(minutes=5)
        self.store.close(t["id"], r["price"], reason, fees, p, when=when.strftime(FMT) if when is not None else None,
                         funding=fund, note=f"exit rebuilt from candles, written {utcnow()}" if late else None)
        self._say(f"{self.tag}EXIT {t['coin']} {'short' if t['short'] else 'long'} {reason} at {r['price']:.6g}"
                  f"{' (happened ' + when.strftime('%m-%d %H:%M') + ' UTC)' if late else ''}  "
                  f"P&L {p:+.2f} USDT{f' incl. funding {-fund:+.2f}' if abs(fund) >= 0.005 else ''}")

    def exits(self, now: pd.Timestamp) -> None:
        open_ = self.store.open_trades()
        hour = now.floor("h")
        if open_ and not self.broker.live and self.audited != hour:
            # first check after a start and once per hour: what the candles say, not what the price is right now
            for t, reason, px, when in self.broker.audit(open_, now):
                self._close(t, reason, px, when)
            open_ = self.store.open_trades()
        self.audited = hour
        for t, px in self.broker.stopped(open_):
            away = self.broker.live and abs(px / t["stop_price"] - 1) > 0.02
            self._close(t, "external" if away else "stop", px)
            if away:
                self._say(f"{self.tag}{t['coin']} was closed outside the trader, away from its stop - recorded as 'external'",
                          logging.WARNING)
        for t in self.broker.unprotected(self.store.open_trades()):
            self._say(f"{self.tag}{t['coin']} is beyond its stop and still open - the exchange stop did not fire, closing now",
                      logging.ERROR)
            self._close(t, "stop_soft")
        for t in self.store.open_trades():
            opened = pd.Timestamp(t["open_time"], tz="UTC").floor("h")
            if now >= opened + pd.Timedelta(hours=ft.HOLD_H):
                self._close(t, "time_48h")

    # ------------------------------------------------------------------ entries
    def _day_halt(self, now: pd.Timestamp) -> bool:
        """Day-loss switch: closed profit of this UTC day + open trades, against the wallet at the day's start."""
        open_ = self.store.open_trades()
        realized = self.store.realized(now.strftime("%Y-%m-%d"))
        px = last_prices(self.ex, [t["coin"] for t in open_]) if open_ else {}
        day = realized + sum(pnl(t, px.get(t["coin"], t["open_price"]), t["fees"] or 0) for t in open_)
        start = self.broker.balance() - realized
        if start <= 0 or day > -DAY_LOSS_HALT * start:
            return False
        until = (now.floor("D") + pd.Timedelta(days=1)).strftime(FMT)
        why = f"day {day:+.2f} USDT is past -{DAY_LOSS_HALT:.0%} of {start:.2f}"
        halt(self.mode, until, why)
        self._say(f"{self.tag}DAY-LOSS HALT: {why}. No new entries until {until} UTC; open trades are still managed. "
                  f"'resume' lifts it.", logging.WARNING)
        return True

    def hourly(self, hour: pd.Timestamp, fresh: bool = True) -> None:
        """fresh: we are within ENTRY_GRACE_S of the candle close. A late start reads the signals but does not enter:
        the research enters at the close, and an entry 45 minutes later is a different trade."""
        frames, failed = all_candles(self.ex, COINS, hour)
        if failed:
            log.warning("candles not read for %s - no signal for them this hour", ",".join(failed))
        ind = {c: ft.indicators(d) for c, d in frames.items()}
        S = ft.signals(ind)
        new = S[S.time == hour - pd.Timedelta(hours=1)]
        log.info("hour %s: %d coins read, %d new signals", hour.strftime("%m-%d %H:%M"), len(frames), len(new))
        if new.empty:
            return
        state = get_state(self.mode)
        if state == "running" and fresh and self._day_halt(pd.Timestamp(datetime.now(timezone.utc))):
            state = "halted"
        foreign = self.broker.foreign(self.store.open_trades()) if state == "running" and fresh else set()
        for s in new.itertuples(index=False):
            side = "short" if s.short else "long"
            if not fresh:
                log.info("signal %s %s skipped - read more than %d s after its candle closed", s.coin, side, ENTRY_GRACE_S)
                continue
            if state != "running":
                log.info("signal %s %s skipped - %s", s.coin, side, state)
                continue
            open_ = self.store.open_trades()
            if any(t["coin"] == s.coin for t in open_):
                log.info("signal %s %s skipped - coin already in a trade", s.coin, side)
                continue
            if s.coin in foreign:
                self._say(f"{self.tag}signal {s.coin} {side} skipped - the account holds a {s.coin} position that is "
                          f"not in the trader's book", logging.WARNING)
                continue
            if len(open_) >= SLOTS:
                log.info("signal %s %s skipped - all %d slots used", s.coin, side, SLOTS)
                continue
            free = self.broker.balance() - sum(t["stake"] for t in open_)
            stake = free / (SLOTS - len(open_))
            try:                                         # stop from the real fill, as in the research
                o = self.broker.open(s.coin, s.short, stake, lambda px, s=s: ft.stop_price(px, s.sig24, s.short))
            except EntryAborted as e:
                self._say(f"{self.tag}ENTRY ABORTED {e}", logging.ERROR)
                continue
            if o is None:
                log.info("signal %s %s skipped - stake %.2f below Binance minimum", s.coin, side, stake)
                continue
            self.store.add(coin=s.coin, short=int(s.short), signal_time=str(s.time), sig24=s.sig24,
                           open_time=utcnow(), open_price=o["price"], amount=o["amount"], stake=o["stake"],
                           stop_price=o["stop_price"], stop_order_id=o["stop_order_id"], fees=o["fees"], note=o.get("note"))
            self._say(f"{self.tag}ENTRY {s.coin} {side} at {o['price']:.6g}, {o['stake']:.2f} USDT x{LEVERAGE}, "
                      f"stop {o['stop_price']:.6g}, exit by 48h")
            if o.get("note"):
                self._say(f"{self.tag}WARNING {s.coin}: {o['note']}", logging.ERROR)

    # ------------------------------------------------------------------ loop
    def tick(self) -> None:
        now = pd.Timestamp(datetime.now(timezone.utc))
        self.exits(now)
        hour = now.floor("h")
        if hour != self.last_hour and now - hour >= pd.Timedelta(seconds=10):
            fresh = (now - hour).total_seconds() <= ENTRY_GRACE_S
            try:
                self.hourly(hour, fresh)
                self.last_hour = hour
            except Exception:
                if not fresh:                            # too late for entries anyway: stop retrying this hour
                    self.last_hour = hour
                raise                                    # still fresh: the next tick (20 s) tries the hour again
        write_atomic(RUNTIME / f"{self.mode}_heartbeat.txt", utcnow())

    def run(self) -> None:
        import msvcrt
        self._lock = open(RUNTIME / f"{self.mode}.lock", "a+")
        try:
            msvcrt.locking(self._lock.fileno(), msvcrt.LK_NBLCK, 1)      # one trader per mode, ever
        except OSError:
            raise SystemExit(f"{self.mode} trader is already running")
        open_ = self.store.open_trades()
        gap = age_min(RUNTIME / f"{self.mode}_heartbeat.txt")
        down = f", was down {gap:.0f} min" if gap is not None and gap > 5 else ""
        self._say(f"{self.tag}trader started, state {get_state(self.mode)}, {len(open_)} open trades{down}")
        try:
            strangers = self.broker.foreign(open_)
            if strangers:
                self._say(f"{self.tag}positions on the account that are not in the trader's book: "
                          f"{', '.join(sorted(strangers))}. Left alone; no new trades in these coins.", logging.WARNING)
        except Exception as e:  # noqa: BLE001 - the check is repeated before every entry
            log.warning("account check at start not done (%s)", type(e).__name__)
        errors = 0
        while True:
            try:
                self.tick()
                errors = 0
            except Exception as e:
                errors += 1
                log.exception("tick failed (%d in a row)", errors)
                if errors in (3, 30) or errors % 180 == 0:            # 1 min, 10 min, then every hour
                    notify.send(f"{self.tag}trader error x{errors}: {type(e).__name__}: {str(e)[:150]}")
            time.sleep(20)


def setup_logging(mode: str) -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    h = RotatingFileHandler(RUNTIME / f"{mode}.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(h)
    log.setLevel(logging.INFO)
