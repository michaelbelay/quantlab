"""Read-only view of the quantlab trader (trader/) for the Trader tab. Never places, changes or cancels anything.

    build(fetch) -> {"modes": {"paper": {...}, "live": {...} or absent}}

Prices come from Binance public endpoints (no key). Open P&L is marked at the last price, fees already paid included.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from trader.engine import get_state, read_state
from trader.fsio import age_min, read_time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "data" / "trader"
START_PAPER = 400.0


def _rows(db: Path, sql: str) -> list[dict]:
    with closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as c:
        c.row_factory = sqlite3.Row
        return [dict(r) for r in c.execute(sql)]


def mode_view(mode: str, prices: dict[str, float]) -> dict | None:
    db = RUNTIME / f"{mode}.sqlite"
    if not db.exists():
        return None
    st = read_state(mode)
    hb = RUNTIME / f"{mode}_heartbeat.txt"
    t = read_time(hb)                                   # None when the file is missing or damaged - never an error
    beat = t.strftime("%Y-%m-%d %H:%M:%S") if t else None
    age = age_min(hb)
    op = _rows(db, "SELECT * FROM trades WHERE close_time IS NULL ORDER BY id")
    cl = _rows(db, "SELECT * FROM trades WHERE close_time IS NOT NULL ORDER BY id")
    for t in op:
        p = prices.get(t["coin"] + "USDT")
        t["price"] = p
        t["upnl"] = None if p is None else round(((t["open_price"] - p) if t["short"] else (p - t["open_price"])) * t["amount"] - t["fees"], 2)
    op.sort(key=lambda t: t["upnl"] if t["upnl"] is not None else 0)          # worst first
    closed = round(sum(t["pnl"] or 0 for t in cl), 2)
    upnl = round(sum(t["upnl"] or 0 for t in op), 2)
    wins = sum((t["pnl"] or 0) > 0 for t in cl)
    state = get_state(mode)                             # running | paused | halted (day-loss switch)
    out = {"state": state, "since": st.get("since_utc"), "heartbeat": beat, "age_min": age,
           "halt_until": st.get("halt_until") if state == "halted" else None,
           "halt_why": st.get("halt_why") if state == "halted" else None,
           "alive": age is not None and age <= 2, "open": op, "closed": cl[::-1][:50],
           "n_closed": len(cl), "wins": wins, "closed_pnl": closed, "open_pnl": upnl,
           "worst_closed": min((t["pnl"] for t in cl), default=None)}
    if mode == "paper":
        out["start"] = START_PAPER
        out["equity"] = round(START_PAPER + closed + upnl, 2)
    log = RUNTIME / f"{mode}.log"
    out["log"] = log.read_text(encoding="utf-8", errors="replace").splitlines()[-12:] if log.exists() else []
    return out


def build(fetch) -> dict:
    prices = {r["symbol"]: float(r["price"]) for r in fetch("/fapi/v1/ticker/price", ttl=10)}
    modes = {m: v for m in ("paper", "live") if (v := mode_view(m, prices)) is not None}
    return {"modes": modes, "at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}


def live_on() -> bool:
    """True while a live trader writes heartbeats (the Today journal logs on/off changes)."""
    age = age_min(RUNTIME / "live_heartbeat.txt")
    return age is not None and age <= 2
