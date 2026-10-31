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
from .broker import LiveBroker, PaperBroker
from .market import all_candles, exchange
from .settings import COINS, FEE, LEVERAGE, PAPER_WALLET, RUNTIME, SLOTS
from .store import Store, utcnow

log = logging.getLogger("trader")


def state_file(mode: str):
    return RUNTIME / f"{mode}_state.json"


def get_state(mode: str) -> str:
    try:
        return json.loads(state_file(mode).read_text())["state"]
    except Exception:
        return "paused"                                   # unknown -> safest


def set_state(mode: str, state: str) -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    state_file(mode).write_text(json.dumps({"state": state, "since_utc": utcnow()}))


def pnl(t: dict, price: float, fees: float) -> float:
    move = (t["open_price"] - price) if t["short"] else (price - t["open_price"])
    return move * t["amount"] - fees


class Engine:
    def __init__(self, mode: str):
        self.mode = mode
        self.tag = "[PAPER] " if mode == "paper" else ""
        self.store = Store(RUNTIME / f"{mode}.sqlite", PAPER_WALLET if mode == "paper" else None)
        if mode == "live":
            keys = vault.get("binance")
            if not keys:
                raise SystemExit("no Binance key saved - run: python -m trader.vault set binance")
            self.ex = exchange(keys)
            self.broker = LiveBroker(self.ex, self.store)
        else:
            self.ex = exchange()
            self.broker = PaperBroker(self.ex, self.store)
        self.last_hour: pd.Timestamp | None = None
        if not state_file(mode).exists():
            set_state(mode, "running" if mode == "paper" else "paused")

    # ------------------------------------------------------------------ exits
    def _close(self, t: dict, reason: str, price: float | None = None) -> None:
        r = self.broker.close(t, reason, price) if reason != "stop" or not self.broker.live else {"price": price, "fees": t["amount"] * price * FEE}
        fees = (t["fees"] or 0) + r["fees"]
        p = pnl(t, r["price"], fees)
        self.store.close(t["id"], r["price"], reason, fees, p)
        msg = f"{self.tag}EXIT {t['coin']} {'short' if t['short'] else 'long'} {reason} at {r['price']:.6g}  P&L {p:+.2f} USDT"
        log.info(msg); notify.send(msg)

    def exits(self, now: pd.Timestamp) -> None:
        open_ = self.store.open_trades()
        for t, px in self.broker.stopped(open_):
            self._close(t, "stop", px)
        for t in self.store.open_trades():
            opened = pd.Timestamp(t["open_time"], tz="UTC").floor("h")
            if now >= opened + pd.Timedelta(hours=ft.HOLD_H):
                self._close(t, "time_48h")

    # ------------------------------------------------------------------ entries
    def hourly(self, hour: pd.Timestamp) -> None:
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
        for s in new.itertuples(index=False):
            side = "short" if s.short else "long"
            if state != "running":
                log.info("signal %s %s skipped - %s", s.coin, side, state)
                continue
            open_ = self.store.open_trades()
            if any(t["coin"] == s.coin for t in open_):
                log.info("signal %s %s skipped - coin already in a trade", s.coin, side)
                continue
            if len(open_) >= SLOTS:
                log.info("signal %s %s skipped - all %d slots used", s.coin, side, SLOTS)
                continue
            free = self.broker.balance() - sum(t["stake"] for t in open_)
            stake = free / (SLOTS - len(open_))
            ref_px = s.close
            stop = ft.stop_price(ref_px, s.sig24, s.short)
            o = self.broker.open(s.coin, s.short, stake, stop)
            if o is None:
                log.info("signal %s %s skipped - stake %.2f below Binance minimum", s.coin, side, stake)
                continue
            stop = ft.stop_price(o["price"], s.sig24, s.short)   # stop from the real fill, as in the research
            self.store.add(coin=s.coin, short=int(s.short), signal_time=str(s.time), sig24=s.sig24,
                           open_time=utcnow(), open_price=o["price"], amount=o["amount"], stake=o["stake"],
                           stop_price=stop, stop_order_id=o["stop_order_id"], fees=o["fees"])
            msg = (f"{self.tag}ENTRY {s.coin} {side} at {o['price']:.6g}, {o['stake']:.2f} USDT x{LEVERAGE}, "
                   f"stop {stop:.6g}, exit by 48h")
            log.info(msg); notify.send(msg)

    # ------------------------------------------------------------------ loop
    def tick(self) -> None:
        now = pd.Timestamp(datetime.now(timezone.utc))
        self.exits(now)
        hour = now.floor("h")
        if hour != self.last_hour and now - hour >= pd.Timedelta(seconds=10):
            self.last_hour = hour
            self.hourly(hour)
        (RUNTIME / f"{self.mode}_heartbeat.txt").write_text(utcnow())

    def run(self) -> None:
        import msvcrt
        self._lock = open(RUNTIME / f"{self.mode}.lock", "a+")
        try:
            msvcrt.locking(self._lock.fileno(), msvcrt.LK_NBLCK, 1)      # one trader per mode, ever
        except OSError:
            raise SystemExit(f"{self.mode} trader is already running")
        msg =f"{self.tag}trader started, state {get_state(self.mode)}, {len(self.store.open_trades())} open trades"
        log.info(msg); notify.send(msg)
        errors = 0
        while True:
            try:
                self.tick()
                errors = 0
            except Exception as e:
                errors += 1
                log.exception("tick failed (%d in a row)", errors)
                if errors in (3, 30):
                    notify.send(f"{self.tag}trader error x{errors}: {type(e).__name__}: {str(e)[:150]}")
            time.sleep(20)


def setup_logging(mode: str) -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    h = RotatingFileHandler(RUNTIME / f"{mode}.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(h)
    log.setLevel(logging.INFO)
