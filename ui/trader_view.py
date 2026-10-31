"""Read-only view of the quantlab trader (trader/) for the Trader tab. Never places, changes or cancels anything.

    build(fetch) -> {"modes": {"paper": {...}, "live": {...} or absent}}

Prices come from Binance public endpoints (no key). Open P&L is marked at the last price, fees already paid included.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "data" / "trader"
START_PAPER = 400.0


def _rows(db: Path, sql: str) -> list[dict]:
    with closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as c:
        c.row_factory = sqlite3.Row
        return [dict(r) for r in c.execute(sql)]


def _age_min(ts: str | None) -> float | None:
    if not ts:
        return None
    t = datetime.strptime(ts.strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return round((datetime.now(timezone.utc) - t).total_seconds() / 60, 1)


def mode_view(mode: str, prices: dict[str, float]) -> dict | None:
    db = RUNTIME / f"{mode}.sqlite"
    if not db.exists():
        return None
    try:
        st = json.loads((RUNTIME / f"{mode}_state.json").read_text())
    except Exception:
        st = {"state": "paused", "since_utc": None}
    hb = RUNTIME / f"{mode}_heartbeat.txt"
    beat = hb.read_text().strip() if hb.exists() else None
    age = _age_min(beat)
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
    out = {"state": st.get("state"), "since": st.get("since_utc"), "heartbeat": beat, "age_min": age,
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
    hb = RUNTIME / "live_heartbeat.txt"
    if not hb.exists():
        return False
    age = _age_min(hb.read_text())
    return age is not None and age <= 2
