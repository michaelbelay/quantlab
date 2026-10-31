"""Trader settings - one place for paths, coins and account rules."""
from __future__ import annotations

import json
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKET = ROOT / "data" / "market"
FUTURES = MARKET / "main" / "binance" / "futures"   # <COIN>_USDT_USDT-<tf>-futures.feather, -1h-funding_rate
RUNTIME = ROOT / "data" / "trader"          # database, state, logs (git-ignored)
SECRETS = ROOT / "secrets"                  # DPAPI-encrypted keys (git-ignored)

COINS = ["BTC", "ETH", "ZEC", "SOL", "XRP", "HYPE", "NEAR", "DOGE", "UNI", "BNB",
         "SUI", "ENA", "1000PEPE", "QNT", "ARB", "WLD", "PUMP", "LINK", "ADA", "TAO"]
SLOTS = 6                 # stake = free balance / free slots
LEVERAGE = 1
PAPER_WALLET = 400.0      # paper starts at about the live account's size
FEE = 0.0005              # taker fee per side (Binance USD-M)


@cache
def _min_costs() -> dict[str, float]:
    rows = json.loads((MARKET / "min_notional_mainnet.json").read_text())["rows"]
    return {r["pair"].split("/")[0]: float(r["cost_min"]) for r in rows}


def min_cost(coin: str) -> float:
    """Binance's minimum order value in USDT, plus 5% for rounding the amount down to the coin's step size."""
    return _min_costs().get(coin, 5.0) * 1.05
