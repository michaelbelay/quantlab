"""Order handling. PaperBroker simulates fills on live prices; LiveBroker sends real orders to Binance USD-M.

Both return the same things, so the engine never knows which one it talks to.
"""
from __future__ import annotations

import logging

import ccxt

from .market import last_prices, symbol
from .settings import FEE, LEVERAGE, min_cost
from .store import Store

log = logging.getLogger("trader")


class PaperBroker:
    live = False

    def __init__(self, ex: ccxt.binanceusdm, store: Store):
        self.ex, self.store = ex, store

    def balance(self) -> float:
        return self.store.paper_balance()

    def open(self, coin: str, short: bool, stake: float, stop: float) -> dict | None:
        px = last_prices(self.ex, [coin]).get(coin)
        if not px or stake < min_cost(coin):
            return None
        return {"price": px, "amount": stake / px, "stake": stake, "fees": stake * FEE, "stop_order_id": None}

    def close(self, t: dict, reason: str, price: float | None = None) -> dict:
        px = price or last_prices(self.ex, [t["coin"]])[t["coin"]]
        return {"price": px, "fees": t["amount"] * px * FEE}

    def stopped(self, trades: list[dict]) -> list[tuple[dict, float]]:
        """Trades whose stop was crossed. Fill = the worse of the stop and the last price (a stop-market can slip)."""
        px = last_prices(self.ex, [t["coin"] for t in trades])
        out = []
        for t in trades:
            p = px.get(t["coin"])
            if p is None:
                continue
            if t["short"] and p >= t["stop_price"]:
                out.append((t, max(p, t["stop_price"])))
            elif not t["short"] and p <= t["stop_price"]:
                out.append((t, min(p, t["stop_price"])))
        return out


class LiveBroker:
    """Real orders: market entry, stop-market on Binance (reduce-only, mark price), market exit.

    Not yet run against the real account - first live use is one minimum-size trade together with Michael.
    """
    live = True

    def __init__(self, ex: ccxt.binanceusdm, store: Store):
        self.ex, self.store = ex, store
        self.ex.load_markets()

    def balance(self) -> float:
        b = self.ex.fetch_balance()
        return float(b["total"].get("USDT", 0.0))

    def _setup(self, sym: str) -> None:
        for call in (lambda: self.ex.set_margin_mode("isolated", sym), lambda: self.ex.set_leverage(LEVERAGE, sym)):
            try:
                call()
            except ccxt.BaseError as e:                  # "no need to change" is an error on Binance
                log.info("setup %s: %s", sym, str(e)[:120])

    def open(self, coin: str, short: bool, stake: float, stop: float) -> dict | None:
        sym = symbol(coin)
        self._setup(sym)
        px = last_prices(self.ex, [coin])[coin]
        amount = float(self.ex.amount_to_precision(sym, stake * LEVERAGE / px))
        if amount * px < min_cost(coin) / 1.05:
            return None
        o = self.ex.create_order(sym, "market", "sell" if short else "buy", amount)
        fill = float(o.get("average") or self.ex.fetch_order(o["id"], sym).get("average") or px)
        amount = float(o.get("filled") or amount)
        so = self.ex.create_order(sym, "STOP_MARKET", "buy" if short else "sell", amount, None,
                                  {"stopPrice": self.ex.price_to_precision(sym, stop), "reduceOnly": True,
                                   "workingType": "MARK_PRICE"})
        return {"price": fill, "amount": amount, "stake": amount * fill / LEVERAGE, "fees": amount * fill * FEE,
                "stop_order_id": str(so["id"])}

    def close(self, t: dict, reason: str, price: float | None = None) -> dict:
        sym = symbol(t["coin"])
        if t.get("stop_order_id"):
            try:
                self.ex.cancel_order(t["stop_order_id"], sym, {"trigger": True})
            except ccxt.BaseError as e:
                log.warning("stop order %s not cancelled: %s", t["stop_order_id"], str(e)[:120])
        o = self.ex.create_order(sym, "market", "buy" if t["short"] else "sell", t["amount"], None, {"reduceOnly": True})
        fill = float(o.get("average") or self.ex.fetch_order(o["id"], sym).get("average") or 0)
        return {"price": fill, "fees": t["amount"] * fill * FEE}

    def stopped(self, trades: list[dict]) -> list[tuple[dict, float]]:
        """Trades whose position is gone on Binance (the exchange stop filled). Fill price from our account trades."""
        if not trades:
            return []
        pos = {p["symbol"]: abs(float(p.get("contracts") or 0)) for p in self.ex.fetch_positions([symbol(t["coin"]) for t in trades])}
        out = []
        for t in trades:
            if pos.get(symbol(t["coin"]), 0) > 0:
                continue
            fills = self.ex.fetch_my_trades(symbol(t["coin"]), limit=20)
            side = "buy" if t["short"] else "sell"
            px = next((float(f["price"]) for f in reversed(fills) if f["side"] == side), t["stop_price"])
            out.append((t, px))
        return out
