r"""Decision log: Michael's own calls on the live bot, and whether they beat the bot left alone.

    add(body, snap, bot_trades) -> dict     not wired since 2026-10-29 (needs an account snapshot; the UI holds no key)
    build(fetch) -> dict                    GET  /api/decisions

Each entry (data/decisions.jsonl, append-only) records WHEN, WHAT HE SAW (insight text + tags), WHAT HE DID
("let_run" or "exit_now") and the account's open positions at that moment (from the exchange, with the bot's stop for
each). Nothing here places, changes or closes anything: an exit is still done with Stop & close.

Scoring, fixed 2026-10-11 before the first entry:
  * exit now  = each position's unrealised P&L at the moment of the decision
  * bot alone = what the same positions would have made without him, judged at HORIZON_H (72 h):
      - if the bot closed the trade itself (its own stop / signal / time exit, not a forced exit) within the horizon:
        the real closed profit
      - otherwise, hourly candles from the decision: the bot's stop price if a candle crossed it, else the close at
        the horizon (still open and horizon not reached -> "pending", shown with the current mark)
  * his result = exit now (if he exited) or bot alone (if he let it run); value added = his result - the other one.
Before fees and funding (both choices pay an exit fee; funding over 72 h is small). The 24 h mark is shown too.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "data" / "decisions.jsonl"
HORIZON_H = 72
ACTIONS = {"let_run": "Let it run", "exit_now": "Exit now"}
TAGS = ("News", "Crowd interest", "Interest falling", "Price action", "Market condition", "Gut feeling")
FORCED = {"force_exit", "emergency_exit", "liquidation"}
_cache: dict[str, tuple[float, dict]] = {}


def _ms(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)


def _read() -> list[dict]:
    if not LOG.exists():
        return []
    out = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def add(body: dict, snap: dict, bot_trades: list[dict], context: dict | None = None) -> dict:
    act = body.get("action")
    if act not in ACTIONS:
        raise ValueError("action must be let_run or exit_now")
    text = str(body.get("insight", "")).strip()
    if not text:
        raise ValueError("write what you see first")
    tags = [t for t in (body.get("tags") or []) if t in TAGS]
    acc = snap.get("account") or {}
    if acc.get("error"):
        raise ValueError(f"account not readable: {acc['error']}")
    pos = acc.get("positions") or []
    if not pos:
        raise ValueError("no open position: nothing to decide about")
    stops = {t.get("pair"): t.get("stop_loss_abs") for t in bot_trades}
    opened = {t.get("pair"): str(t.get("open_date") or "")[:19] for t in bot_trades}
    e = {"id": int(time.time() * 1000), "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "action": act, "insight": text[:1000], "tags": tags, "strategy": snap.get("strategy"),
         "equity": acc.get("equity_usdt"), "upnl": acc.get("upnl_usdt"),
         "positions": [{"symbol": p["symbol"], "side": p["side"], "contracts": float(p["contracts"]),
                        "entry": float(p["entry"]), "mark": float(p["mark"]), "upnl": float(p["upnl"] or 0),
                        "stop": stops.get(p["symbol"]), "open_date": opened.get(p["symbol"])} for p in pos],
         # what the insights panel showed at that moment, so later we can see which readings were worth acting on
         "insights": {x["symbol"]: {k: x.get(k) for k in ("chg_24h", "oi_24h", "funding", "vol_ratio", "taker_buy", "ls_ratio")}
                      | {"reads": [q["text"] for q in x.get("reads", [])], "tilt": (x.get("tilt") or {}).get("word")}
                      for x in (context or {}).get("rows", [])}}
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
    _cache.clear()
    return {"ok": True, "entry": e}


def _bot_alone(p: dict, t0: int, fetch, closed: dict) -> tuple[float | None, float | None, str]:
    """(value at 24 h, value at the horizon or None if pending, how) for one position."""
    sign = 1 if p["side"] == "long" else -1
    q, entry, stop = p["contracts"], p["entry"], p["stop"]
    pnl = lambda price: sign * (price - entry) * q
    c = closed.get((p["symbol"], p.get("open_date")))
    if c and c.get("exit_reason") not in FORCED and c.get("close_date"):
        ct = _ms(str(c["close_date"]).replace(" ", "T") + ("" if "+" in str(c["close_date"]) else "+00:00"))
        if ct <= t0 + HORIZON_H * 3600_000:
            v = float(c.get("close_profit_abs") or 0)
            return v, v, f"bot closed it ({c.get('exit_reason')})"
    from urllib.parse import quote
    sym = quote(p["symbol"].split("/")[0] + "USDT")
    k = fetch(f"/fapi/v1/klines?symbol={sym}&interval=1h&startTime={t0 - t0 % 3600_000}&limit={HORIZON_H + 2}", ttl=300) or []
    v24, now = None, time.time() * 1000
    for row in k:
        ot, hi, lo, cl = int(row[0]), float(row[2]), float(row[3]), float(row[4])
        if ot + 3600_000 <= t0:
            continue
        if stop and ((sign > 0 and lo <= stop) or (sign < 0 and hi >= stop)):
            v = pnl(stop)
            return (v if v24 is None else v24), v, "bot's stop"
        if v24 is None and ot + 3600_000 >= t0 + 24 * 3600_000:
            v24 = pnl(cl)
        if ot + 3600_000 >= t0 + HORIZON_H * 3600_000:
            return v24, pnl(cl), f"price at {HORIZON_H} h"
    last = pnl(float(k[-1][4])) if k else None
    if now < t0 + HORIZON_H * 3600_000:
        return v24, None, f"pending, now {last:+.2f}" if last is not None else "pending"
    return v24, last, "last price"


def _closed_trades() -> dict:
    """Closed trades of the earlier live bots (copies in data/history, read-only), keyed by (pair, open_date)."""
    import sqlite3
    out = {}
    try:
        for db in (ROOT / "data" / "history").glob("live_*.sqlite"):
            if not db.exists():
                continue
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            for pair, od, cd, cpa, er in con.execute(
                    "select pair, open_date, close_date, close_profit_abs, exit_reason from trades where is_open = 0"):
                out[(pair, str(od)[:19])] = {"close_date": cd, "close_profit_abs": cpa, "exit_reason": er}
            con.close()
    except Exception:
        pass
    return out


def build(fetch) -> dict:
    hit = _cache.get("b")
    if hit and time.time() - hit[0] < 120:
        return hit[1]
    closed = _closed_trades()
    rows, tot = [], {"n": 0, "scored": 0, "added": 0.0, "better": 0}
    for e in reversed(_read()):
        t0 = _ms(e["at"])
        now_v = sum(p["upnl"] for p in e["positions"])
        parts = [(p, *_bot_alone(p, t0, fetch, closed)) for p in e["positions"]]
        pending = any(h is None for _, _, h, _ in parts)
        alone = None if pending else sum(h for _, _, h, _ in parts)
        a24 = None if any(v is None for _, v, _, _ in parts) else sum(v for _, v, _, _ in parts)
        mine = (now_v if e["action"] == "exit_now" else alone)
        other = (alone if e["action"] == "exit_now" else now_v)
        added = None if mine is None or other is None else mine - other
        tot["n"] += 1
        if added is not None:
            tot["scored"] += 1
            tot["added"] += added
            tot["better"] += added > 0
        rows.append({**e, "label": ACTIONS[e["action"]], "exit_now_value": round(now_v, 2),
                     "bot_alone_24h": None if a24 is None else round(a24, 2),
                     "bot_alone": None if alone is None else round(alone, 2), "pending": pending,
                     "value_added": None if added is None else round(added, 2),
                     "how": [{"symbol": p["symbol"], "how": h} for p, _, _, h in parts]})
    tot["added"] = round(tot["added"], 2)
    out = {"rows": rows, "total": tot, "tags": TAGS, "actions": ACTIONS, "horizon_h": HORIZON_H}
    _cache["b"] = (time.time(), out)
    return out
