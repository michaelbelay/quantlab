"""Order handling. PaperBroker simulates fills on live prices; LiveBroker sends real orders to Binance USD-M.

Both return the same things, so the engine never knows which one it talks to.

Paper fills are charged like the research: fee + slippage per side (settings.FEE, settings.SLIPPAGE); funding is
added by the engine at the exit. Paper exits are also rebuilt from candles (audit), so a stop touched between two
price checks, or while the trader was not running at all, is still filled where the rule says it fills.
"""
from __future__ import annotations

import logging
import time
from typing import Callable

import ccxt
import pandas as pd

from .flowtrend import HOLD_H
from .market import hourly, last_prices, symbol
from .settings import FEE, LEVERAGE, SLIPPAGE, SOFT_STOP_TICKS, min_cost
from .store import Store

log = logging.getLogger("trader")
H1 = pd.Timedelta(hours=1)


class EntryAborted(Exception):
    """The entry was sent but could not be protected, and was closed again. Nothing is left open."""


def _slip(px: float, buying: bool) -> float:
    return px * (1 + SLIPPAGE) if buying else px * (1 - SLIPPAGE)


def beyond(t: dict, px: float) -> bool:
    return px >= t["stop_price"] if t["short"] else px <= t["stop_price"]


class PaperBroker:
    live = False

    def __init__(self, ex: ccxt.binanceusdm, store: Store):
        self.ex, self.store = ex, store

    def balance(self) -> float:
        return self.store.paper_balance()

    def open(self, coin: str, short: bool, stake: float, stop_of: Callable[[float], float]) -> dict | None:
        px = last_prices(self.ex, [coin]).get(coin)
        if not px or stake < min_cost(coin):
            return None
        fill = _slip(px, buying=not short)
        return {"price": fill, "amount": stake / fill, "stake": stake, "fees": stake * FEE,
                "stop_price": stop_of(fill), "stop_order_id": None}

    def close(self, t: dict, reason: str, price: float | None = None) -> dict:
        px = price or last_prices(self.ex, [t["coin"]])[t["coin"]]
        fill = _slip(px, buying=bool(t["short"]))
        return {"price": fill, "fees": t["amount"] * fill * FEE}

    def stopped(self, trades: list[dict]) -> list[tuple[dict, float]]:
        """Trades whose stop was crossed. Fill = the worse of the stop and the last price (a stop-market can slip)."""
        px = last_prices(self.ex, [t["coin"] for t in trades])
        out = []
        for t in trades:
            p = px.get(t["coin"])
            if p is None:
                continue
            if beyond(t, p):
                out.append((t, max(p, t["stop_price"]) if t["short"] else min(p, t["stop_price"])))
        return out

    def unprotected(self, trades: list[dict]) -> list[dict]:
        return []

    def foreign(self, trades: list[dict]) -> set[str]:
        return set()

    def audit(self, trades: list[dict], now: pd.Timestamp) -> list[tuple[dict, str, float | None, pd.Timestamp]]:
        """Exits the rule has ALREADY made, read from candles instead of from the price at this moment.

        For every open trade, walk its 1h candles from the entry to now (or to the 48h exit, whichever is first):
          - the first candle whose high (short) / low (long) reaches the stop  -> stop, filled at the stop, or at
            that candle's open when it opened beyond the stop (a gap);
          - no such candle and the 48 hours are over                            -> time exit at the open of the candle
            that starts at the exit hour.
        In the entry hour only the minutes after the entry count (1m candles).
        Returns (trade, reason, price before slippage or None = use the last price, time the exit happened).
        So the paper book does not depend on the trader having been awake: after a crash, a reboot or a week of
        downtime the trades close where and when the research would have closed them.
        """
        out = []
        for t in trades:
            try:
                hit = self._replay(t, now)
            except Exception as e:  # noqa: BLE001 - one coin's candles failing must not block the others
                log.warning("audit %s not done (%s: %s) - price checks still run", t["coin"], type(e).__name__, str(e)[:100])
                continue
            if hit:
                out.append((t, *hit))
        return out

    def _replay(self, t: dict, now: pd.Timestamp):
        opened = pd.Timestamp(t["open_time"], tz="UTC")
        h0 = opened.floor("h")
        due = h0 + pd.Timedelta(hours=HOLD_H)
        k = hourly(self.ex, t["coin"], h0, limit=min(1500, int((min(now, due) - h0) / H1) + 3))
        for ts, c in k.iterrows():
            if ts >= due or ts > now:
                break
            hi, lo, op = c["high"], c["low"], c["open"]
            if ts == h0:
                m = hourly(self.ex, t["coin"], opened.ceil("min"), "1m", 61)
                m = m[m.index < h0 + H1]
                if m.empty:
                    continue
                hi, lo, op = m["high"].max(), m["low"].min(), m["open"].iloc[0]
            if (hi >= t["stop_price"]) if t["short"] else (lo <= t["stop_price"]):
                px = max(t["stop_price"], op) if t["short"] else min(t["stop_price"], op)
                return "stop", float(px), min(ts + H1, now)
        if now >= due:
            return "time_48h", (float(k.at[due, "open"]) if due in k.index else None), due
        return None


class LiveBroker:
    """Real orders: market entry, stop-market on Binance (reduce-only, mark price), market exit.

    Not yet run against the real account - first live use is one minimum-size trade together with Michael.
    """
    live = True

    def __init__(self, ex: ccxt.binanceusdm, store: Store):
        self.ex, self.store = ex, store
        self.ex.load_markets()
        self._beyond: dict[int, int] = {}

    def balance(self) -> float:
        b = self.ex.fetch_balance()
        return float(b["total"].get("USDT", 0.0))

    def _setup(self, sym: str) -> None:
        for call in (lambda: self.ex.set_margin_mode("isolated", sym), lambda: self.ex.set_leverage(LEVERAGE, sym)):
            try:
                call()
            except ccxt.BaseError as e:                  # "no need to change" is an error on Binance
                log.info("setup %s: %s", sym, str(e)[:120])

    def _fill(self, o: dict, sym: str, fallback: float) -> float:
        px = o.get("average")
        if not px:
            try:
                px = self.ex.fetch_order(o["id"], sym).get("average")
            except ccxt.BaseError as e:
                log.warning("fill price of order %s not read: %s", o.get("id"), str(e)[:120])
        return float(px or fallback)

    def open(self, coin: str, short: bool, stake: float, stop_of: Callable[[float], float]) -> dict | None:
        """Market entry, then the stop from the REAL fill. A position is never left without protection silently:
        the stop order is tried twice; if Binance refuses it, the position is closed again at once (EntryAborted);
        if even that fails, the trade is recorded with no stop order and the engine guards it by price checks."""
        sym = symbol(coin)
        self._setup(sym)
        px = last_prices(self.ex, [coin])[coin]
        amount = float(self.ex.amount_to_precision(sym, stake * LEVERAGE / px))
        if amount * px < min_cost(coin) / 1.05:
            return None
        o = self.ex.create_order(sym, "market", "sell" if short else "buy", amount)
        fill = self._fill(o, sym, px)
        amount = float(o.get("filled") or amount)
        stop = stop_of(fill)
        out = {"price": fill, "amount": amount, "stake": amount * fill / LEVERAGE, "fees": amount * fill * FEE,
               "stop_price": stop, "stop_order_id": None}
        why = ""
        for attempt in (1, 2):
            try:
                so = self.ex.create_order(sym, "STOP_MARKET", "buy" if short else "sell", amount, None,
                                          {"stopPrice": self.ex.price_to_precision(sym, stop), "reduceOnly": True,
                                           "workingType": "MARK_PRICE"})
                out["stop_order_id"] = str(so["id"])
                return out
            except ccxt.BaseError as e:
                why = f"{type(e).__name__}: {str(e)[:120]}"
                log.error("stop order for %s refused (try %d): %s", coin, attempt, why)
                time.sleep(1)
        try:
            self.ex.create_order(sym, "market", "buy" if short else "sell", amount, None, {"reduceOnly": True})
        except ccxt.BaseError as e:
            log.error("emergency close of %s refused too: %s", coin, str(e)[:120])
            out["note"] = f"NO EXCHANGE STOP ({why}); emergency close refused too - guarded by price checks"
            return out
        raise EntryAborted(f"{coin}: stop order refused twice ({why}) - position closed again at market")

    def close(self, t: dict, reason: str, price: float | None = None) -> dict:
        sym = symbol(t["coin"])
        if t.get("stop_order_id"):
            try:
                self.ex.cancel_order(t["stop_order_id"], sym, {"trigger": True})
            except ccxt.BaseError as e:
                log.warning("stop order %s not cancelled: %s", t["stop_order_id"], str(e)[:120])
        o = self.ex.create_order(sym, "market", "buy" if t["short"] else "sell", t["amount"], None, {"reduceOnly": True})
        fill = self._fill(o, sym, price or last_prices(self.ex, [t["coin"]]).get(t["coin"]) or t["open_price"])
        self._beyond.pop(t["id"], None)
        return {"price": fill, "fees": t["amount"] * fill * FEE}

    def _held(self, syms: list[str] | None = None) -> dict[str, float]:
        return {p["symbol"]: abs(float(p.get("contracts") or 0)) for p in self.ex.fetch_positions(syms)}

    def stopped(self, trades: list[dict]) -> list[tuple[dict, float]]:
        """Trades whose position is gone on Binance. Price = the average of our closing fills since the entry
        (the engine calls it a stop only when that price is at the stop; anything else is recorded as 'external')."""
        if not trades:
            return []
        pos = self._held([symbol(t["coin"]) for t in trades])
        out = []
        for t in trades:
            if pos.get(symbol(t["coin"]), 0) > 0:
                continue
            self._beyond.pop(t["id"], None)
            since = int(pd.Timestamp(t["open_time"], tz="UTC").timestamp() * 1000)
            side = "buy" if t["short"] else "sell"
            fills = [f for f in self.ex.fetch_my_trades(symbol(t["coin"]), since=since, limit=100) if f["side"] == side]
            qty = sum(float(f["amount"]) for f in fills)
            px = sum(float(f["price"]) * float(f["amount"]) for f in fills) / qty if qty else t["stop_price"]
            out.append((t, px))
        return out

    def unprotected(self, trades: list[dict]) -> list[dict]:
        """Positions still open although the price has been beyond the stop on SOFT_STOP_TICKS checks in a row:
        the exchange stop is missing or did not fire. The engine closes these itself."""
        px = last_prices(self.ex, [t["coin"] for t in trades])
        out = []
        for t in trades:
            p = px.get(t["coin"])
            n = self._beyond.get(t["id"], 0) + 1 if p is not None and beyond(t, p) else 0
            self._beyond[t["id"]] = n
            if n >= SOFT_STOP_TICKS:
                out.append(t)
        return out

    def foreign(self, trades: list[dict]) -> set[str]:
        """Coins with a position on the account that the trader's own book does not explain: a manual trade, or an
        entry whose record was lost. The trader never touches these and takes no new trade in that coin."""
        mine = {symbol(t["coin"]) for t in trades}
        return {s.split("/")[0] for s, n in self._held().items() if n > 0 and s not in mine}
