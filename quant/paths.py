"""Where data lives - everything under C:\\quantlab."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKET = ROOT / "data" / "market"
RESEARCH = ROOT / "research"
FUT = MARKET / "dev_1h" / "binance" / "futures"         # dev coins: <C>_USDT_USDT-1h-{futures,funding_rate}.feather
OOS = MARKET / "extra_coins_1h"                         # extra coins: <SYM>/{ohlcv_1h,funding}.feather
MIN_NOTIONAL = MARKET / "min_notional_mainnet.json"
SPLIT = MARKET / "universe" / "split_140.json"
OOS_UNIVERSE = RESEARCH / "pipeline" / "oos_universe.json"
DESK = MARKET / "desk"

DATA = ROOT / "data"
RUNS = ROOT / "runs"


def dev_coins() -> list[str]:
    """133 development coins (bare names, e.g. 'BTC') that have 1h futures data."""
    s = json.loads(SPLIT.read_text(encoding="utf-8"))
    return [c for c in s["dev"] + s["holdout"] if (FUT / f"{c}_USDT_USDT-1h-futures.feather").exists()]


def oos_coins() -> list[str]:
    """280 extra coins (bare names) - validation only."""
    kept = json.loads(OOS_UNIVERSE.read_text(encoding="utf-8"))["kept"]
    return [s[:-4] for s in kept if (OOS / s / "ohlcv_1h.feather").exists()]
