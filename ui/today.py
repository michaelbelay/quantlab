"""Today view: market condition, feeds, strategy fit and the trading journal.

Everything here is information. Nothing places an order or changes a bot.

    build(fetch, tickers, live_on) -> dict      the /api/today payload
    add_note(text, mood) -> dict                POST /api/journal

Market condition = the two definitions the strategies were tested with (2026-10-11):
    Bull / Bear  BTC 20-day return > 0 / <= 0 at the last completed UTC daily close (the live MajorsTrend rule)
    Wild / Calm  BTC 20-day volatility (std of daily returns) > / <= its median over the previous 365 days
Strategy fit comes from catalog.json (test results only, no opinions).
The journal is data/journal.jsonl: Michael's notes plus automatic entries (condition change, live bot on/off).
"""
from __future__ import annotations

import json
import statistics
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog.json"
JOURNAL = ROOT / "data" / "journal.jsonl"
MOODS = {"calm": "😌", "focused": "🎯", "confident": "💪", "excited": "🚀", "tense": "😬", "tired": "😴", "unsure": "🤔"}
CELL_TEXT = {
    "Bull-Calm": "Prices trending up, moves orderly. Breakouts tend to follow through.",
    "Bull-Wild": "Prices trending up, but swinging hard. Breakouts often reverse.",
    "Bear-Calm": "Prices drifting down, moves orderly. Bounces are short.",
    "Bear-Wild": "Prices falling fast with big swings. Capital protection first.",
}
_jlock = threading.Lock()
TAPE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "HYPEUSDT", "SUIUSDT", "ADAUSDT",
        "LINKUSDT", "AVAXUSDT", "ZECUSDT", "LTCUSDT", "TRXUSDT"]


# ------------------------------------------------------------------ market condition
def _daily(fetch, symbol: str, limit: int = 420) -> list[tuple[int, float]]:
    k = fetch(f"/fapi/v1/klines?symbol={symbol}&interval=1d&limit={limit}", ttl=600)
    now_ms = time.time() * 1000
    return [(int(r[0]), float(r[4])) for r in k if int(r[6]) < now_ms]          # completed candles only


def _day(ms: int) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(ms / 1000))


def _std(x: list[float]) -> float:
    m = sum(x) / len(x)
    return (sum((v - m) ** 2 for v in x) / len(x)) ** 0.5


_cond_cache: dict = {}


def condition(fetch) -> dict:
    hit = _cond_cache.get("v")
    if hit and time.time() - hit[0] < 300:
        return hit[1]
    out = _condition(fetch)
    _cond_cache["v"] = (time.time(), out)
    return out


def _condition(fetch) -> dict:
    d = _daily(fetch, "BTCUSDT", 520)
    closes = [c for _, c in d]
    rets = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))]       # rets[i-1] ends at day i
    vols = [None] * 21 + [_std(rets[i - 20:i]) for i in range(21, len(closes))]      # vols[i]: 20 daily returns ending day i
    rows = []
    for i in range(386, len(closes)):
        vol20 = vols[i]
        hist = vols[i - 365:i]
        med = statistics.median(hist)
        r20 = closes[i] / closes[i - 20] - 1
        cell = ("Bull" if r20 > 0 else "Bear") + "-" + ("Wild" if vol20 > med else "Calm")
        rows.append({"t": d[i][0], "day": _day(d[i][0]), "ret20": r20, "vol": vol20, "med": med, "ratio": vol20 / med, "cell": cell})
    cur = rows[-1]
    since = cur["day"]
    for r in reversed(rows):
        if r["cell"] != cur["cell"]:
            break
        since = r["day"]
    return {"cell": cur["cell"], "bull": cur["ret20"] > 0, "wild": cur["ratio"] > 1, "ret20": round(cur["ret20"] * 100, 2),
            "vol_ratio": round(cur["ratio"], 3), "vol_daily_pct": round(cur["vol"] * 100, 2), "as_of": cur["day"],
            "since": since, "days": sum(1 for _ in _streak(rows)), "btc_close": closes[-1], "text": CELL_TEXT[cur["cell"]],
            "trail": [{"day": r["day"], "x": round(r["ret20"] * 100, 2), "y": round(r["ratio"], 3), "cell": r["cell"]} for r in rows[-90:]]}


def _streak(rows):
    cell = rows[-1]["cell"]
    for r in reversed(rows):
        if r["cell"] != cell:
            return
        yield r


# ------------------------------------------------------------------ feeds
def feeds(tickers: list[dict]) -> dict:
    top = [t for t in tickers if not t["symbol"].startswith(("USDC", "FDUSD"))][:100]
    by = {t["symbol"]: t for t in tickers}
    tape = [{"s": s, "last": by[s]["last"], "chg": round(by[s]["chg"], 2)} for s in TAPE if s in by]
    liquid = top[:60]
    movers = sorted(liquid, key=lambda t: -t["chg"])
    fund = sorted(liquid, key=lambda t: -t["funding"])
    up = sum(1 for t in top if t["chg"] > 0)
    avg_f = statistics.median([t["funding"] for t in top[:50]]) if top else 0.0          # median: one extreme coin cannot skew it
    pick = lambda t: {"s": t["symbol"].replace("USDT", ""), "chg": round(t["chg"], 2), "last": t["last"], "funding": round(t["funding"] * 100, 4)}
    return {"tape": tape, "gainers": [pick(t) for t in movers[:5]], "losers": [pick(t) for t in movers[-5:][::-1]],
            "funding_high": [pick(t) for t in fund[:3]], "funding_low": [pick(t) for t in fund[-3:][::-1]],
            "breadth": {"up": up, "of": len(top), "pct": round(100 * up / max(1, len(top)))},
            "avg_funding_pct": round(avg_f * 100, 4)}


# ------------------------------------------------------------------ strategies
def strategies(fetch, cond: dict) -> list[dict]:
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    out = []
    for s in cat["strategies"]:
        fit = dict(s.get("fit", {}).get(cond["cell"], {"level": "unknown", "why": "Not tested in this condition."}))
        if s.get("fit_rule") == "majors_trend":
            held = []
            for sym in ("BTCUSDT", "ETHUSDT", "BNBUSDT"):
                c = [x for _, x in _daily(fetch, sym, 40)]
                if c[-1] / c[-21] - 1 > 0:
                    held.append(sym.replace("USDT", ""))
            fit = {"level": "good" if held else "cash",
                   "why": f"Its rule would hold {', '.join(held)} today (20-day trend up)." if held
                   else "Its rule would hold nothing today: all three 20-day trends are down. Cash is its plan."}
        out.append({**{k: v for k, v in s.items() if k != "fit"}, "today": fit})
    return out


def suggestions(cond: dict, f: dict, strats: list[dict]) -> list[dict]:
    """Plain sentences from facts and test results only."""
    s = []
    good = [x["name"] for x in strats if x["today"]["level"] == "good"]
    avoid = [x["name"] for x in strats if x["today"]["level"] == "avoid"]
    if good:
        s.append({"tone": "good", "text": f"Suits today's {cond['cell'].replace('-', ' + ').lower()} market: {', '.join(good)}."})
    if avoid:
        s.append({"tone": "warn", "text": f"Tested weak in this condition: {', '.join(avoid)}."})
    r = cond["vol_ratio"]
    if not cond["wild"] and r > 0.85:
        s.append({"tone": "warn", "text": f"Volatility is at {r * 100:.0f}% of its yearly median: close to switching to wild."})
    elif cond["wild"] and r < 1.15:
        s.append({"tone": "info", "text": f"Volatility is at {r * 100:.0f}% of its yearly median: close to calming down."})
    if abs(cond["ret20"]) < 2:
        s.append({"tone": "info", "text": f"BTC's 20-day trend is only {cond['ret20']:+.1f}%: the bull/bear line is near."})
    if f["avg_funding_pct"] > 0.02:
        s.append({"tone": "warn", "text": f"Median funding {f['avg_funding_pct']:.3f}% per 8h: longs are crowded."})
    elif f["avg_funding_pct"] < -0.005:
        s.append({"tone": "info", "text": f"Median funding {f['avg_funding_pct']:.3f}% per 8h: shorts are paying, sellers crowded."})
    b = f["breadth"]["pct"]
    if b >= 75 or b <= 25:
        s.append({"tone": "info", "text": f"{b}% of the top {f['breadth']['of']} coins are up in 24h: a one-sided day."})
    s.append({"tone": "muted", "text": "Information only. Nothing here places an order."})
    return s


# ------------------------------------------------------------------ journal
def _read_journal(limit: int = 200) -> list[dict]:
    if not JOURNAL.exists():
        return []
    rows = []
    for line in JOURNAL.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows[-limit:]


def _append(entry: dict) -> dict:
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    entry = {"t": int(time.time() * 1000), **entry}
    with _jlock, JOURNAL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def _auto(cond: dict, live_on: bool) -> None:
    rows = _read_journal(500)
    last_cell = next((r.get("cell") for r in reversed(rows) if r.get("kind") == "condition"), None)
    if last_cell != cond["cell"]:
        text = (f"Market is {cond['cell'].replace('-', ' + ')} (BTC 20d {cond['ret20']:+.1f}%, volatility "
                f"{cond['vol_ratio'] * 100:.0f}% of median)." if last_cell is None else
                f"Market changed: {last_cell.replace('-', ' + ')} → {cond['cell'].replace('-', ' + ')} "
                f"(BTC 20d {cond['ret20']:+.1f}%, volatility {cond['vol_ratio'] * 100:.0f}% of median).")
        _append({"kind": "condition", "cell": cond["cell"], "text": text})
    last_live = next((r.get("on") for r in reversed(rows) if r.get("kind") == "bot"), None)
    if last_live is not None and last_live != live_on or last_live is None and live_on:
        _append({"kind": "bot", "on": live_on, "text": "Live trader started." if live_on else "Live trader stopped."})


def add_note(text: str, mood: str | None) -> dict:
    text = (text or "").strip()
    if not text:
        raise ValueError("empty note")
    if len(text) > 4000:
        raise ValueError("note too long (4000 characters max)")
    if mood and mood not in MOODS:
        raise ValueError("unknown mood")
    return _append({"kind": "note", "text": text, "mood": mood})


# ------------------------------------------------------------------ payload
def build(fetch, tickers, live_on: bool) -> dict:
    cond = condition(fetch)
    f = feeds(tickers)
    st = strategies(fetch, cond)
    try:
        _auto(cond, live_on)
    except OSError:
        pass
    j = _read_journal(120)[::-1]
    return {"condition": cond, "feeds": f, "strategies": st, "suggestions": suggestions(cond, f, st),
            "journal": j, "moods": MOODS, "live_on": live_on, "generated": int(time.time() * 1000)}
