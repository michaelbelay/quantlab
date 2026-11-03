r"""Quantlab UI server (stdlib only). Serves the UI and a small read-only JSON API.

    .venv\Scripts\python.exe ui\server.py          (or start_ui.bat)  ->  http://localhost:8500

Market data: Binance USDT-M futures PUBLIC endpoints (no key), cached a few seconds.
Research: reads C:\quantlab\runs and research\ outputs. Never writes to either,
except that "Run scan" starts the scanner (it writes its own latest_scan.json).
Trader: read-only view of the quantlab trader (trader/, data/trader); Pause/Resume only write its state file.
No Binance key is used anywhere in this server.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np

# Children get a hidden console, so nothing flashes even when this server itself runs without a window.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import today  # noqa: E402
import decisions  # noqa: E402
import insights  # noqa: E402
import trader_view  # noqa: E402
from trader.engine import get_state, set_state  # noqa: E402
RES = ROOT / "research"
PY = ROOT / ".venv" / "Scripts" / "python.exe"
OPP = RES / "opportunity"
FAPI = "https://fapi.binance.com"
PORT = 8500

_cache: dict[str, tuple[float, object]] = {}
_lock = threading.Lock()
_scan = {"proc": None, "started": None}


def fetch(path: str, ttl: float = 5.0):
    now = time.time()
    with _lock:
        hit = _cache.get(path)
        if hit and now - hit[0] < ttl:
            return hit[1]
    req = urllib.request.Request(FAPI + path, headers={"User-Agent": "quantlab-ui"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.load(r)
    with _lock:
        _cache[path] = (now, data)
    return data


_swr_busy: set[str] = set()


def _swr_store(key: str, fn):
    try:
        val = fn()
        with _lock:
            _cache[key] = (time.time(), val)
        return val
    finally:
        _swr_busy.discard(key)


def swr(key: str, fn, ttl: float, max_stale: float | None = None):
    """Answer from memory at once; when the answer is older than ttl, read a new one in the background for the next
    request. Only the very first request (or one after an error) waits. An answer older than max_stale (nobody looked
    for a while, e.g. overnight) is not shown: that request waits for a fresh one."""
    with _lock:
        hit = _cache.get(key)
        age = time.time() - hit[0] if hit else None
        if hit and age < ttl:
            return hit[1]
        if hit and (max_stale is None or age < max_stale or key in _swr_busy):
            if key not in _swr_busy:
                _swr_busy.add(key)
                threading.Thread(target=lambda: _swr_store(key, fn), daemon=True).start()
            return hit[1]
        _swr_busy.add(key)
    try:
        return _swr_store(key, fn)
    except Exception:  # noqa: BLE001 - a failed refresh of an old answer still shows the old answer
        if hit:
            return hit[1]
        raise


def warm():
    """Fill the slow answers right after start so the first tab click does not wait."""
    for key, fn in (("t:today", _today), ("t:majors", majors), ("t:forward", forward)):
        try:
            swr(key, fn, 0)
        except Exception:  # noqa: BLE001 - the request path reports errors
            pass


def _today():
    return today.build(fetch, tickers(), trader_view.live_on())


# ------------------------------------------------------------------ market week (information only)
def market_week() -> dict:
    """The live MajorsTrend BTC rule: bull while BTC's 20-day return at the last completed UTC daily close is > 0."""
    k = fetch("/fapi/v1/klines?symbol=BTCUSDT&interval=1d&limit=120", ttl=600)
    now_ms = time.time() * 1000
    closes = [(int(r[0]), float(r[4])) for r in k if int(r[6]) < now_ms]     # completed daily candles only
    sig = [(closes[i][0], closes[i][1] / closes[i - 20][1] - 1) for i in range(20, len(closes))]
    t, ret = sig[-1]
    bull = ret > 0
    since = t
    for tt, rr in reversed(sig):
        if (rr > 0) != bull:
            break
        since = tt
    day = lambda ms: time.strftime("%Y-%m-%d", time.gmtime(ms / 1000))
    return {"bull": bull, "ret20": round(100 * ret, 2), "close": closes[-1][1], "as_of": day(t), "since": day(since),
            "complete": since != sig[0][0]}


def trader() -> dict:
    d = trader_view.build(fetch)
    try:
        d["market"] = market_week()
    except Exception as e:  # noqa: BLE001 - the tab must load without it
        d["market"] = {"error": str(e)}
    return d


def trader_action(body: dict) -> dict:
    """Pause / resume new entries. Paper: both. Live: pause only (starting real money stays a terminal step)."""
    mode, act = body.get("mode"), body.get("action")
    if (mode, act) not in (("paper", "pause"), ("paper", "resume"), ("live", "pause")):
        return {"error": f"not allowed here: {mode} {act}"}
    if body.get("confirm") != act.upper():
        return {"error": f"type {act.upper()} to confirm"}
    set_state(mode, "paused" if act == "pause" else "running")
    return {"mode": mode, "state": get_state(mode)}


# ------------------------------------------------------------------ market
def tickers():
    info = fetch("/fapi/v1/exchangeInfo", ttl=3600)
    ok = {s["symbol"] for s in info["symbols"] if s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT"
          and s.get("status") == "TRADING" and s.get("underlyingType", "COIN") == "COIN"}
    t = fetch("/fapi/v1/ticker/24hr", ttl=8)
    prem = {p["symbol"]: p for p in fetch("/fapi/v1/premiumIndex", ttl=8)}
    rows = []
    for x in t:
        if x["symbol"] not in ok:
            continue
        p = prem.get(x["symbol"], {})
        rows.append({"symbol": x["symbol"], "last": float(x["lastPrice"]), "chg": float(x["priceChangePercent"]),
                     "qv": float(x["quoteVolume"]), "high": float(x["highPrice"]), "low": float(x["lowPrice"]),
                     "funding": float(p.get("lastFundingRate") or 0), "next_funding": int(p.get("nextFundingTime") or 0),
                     "mark": float(p.get("markPrice") or 0)})
    rows.sort(key=lambda r: -r["qv"])
    return rows


def klines(symbol: str, interval: str, limit: int):
    k = fetch(f"/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={min(limit, 1500)}", ttl=4)
    return [{"time": int(r[0] // 1000), "open": float(r[1]), "high": float(r[2]), "low": float(r[3]),
             "close": float(r[4]), "volume": float(r[5]), "qvol": float(r[7]), "taker_buy": float(r[9])} for r in k]


def funding(symbol: str):
    f = fetch(f"/fapi/v1/fundingRate?symbol={symbol}&limit=1000", ttl=300)
    return [{"time": int(r["fundingTime"] // 1000), "value": float(r["fundingRate"]) * 100} for r in f]


def oi(symbol: str):
    cur = fetch(f"/fapi/v1/openInterest?symbol={symbol}", ttl=10)
    hist = fetch(f"/futures/data/openInterestHist?symbol={symbol}&period=1h&limit=200", ttl=120)
    return {"now": float(cur["openInterest"]),
            "hist": [{"time": int(r["timestamp"] // 1000), "value": float(r["sumOpenInterestValue"])} for r in hist]}


# ------------------------------------------------------------------ strategy
def majors():
    """MajorsTrend live rule on today's data: long while 20-day return > 0; weight = min(40%/vol30, 2)/3, 1x cap."""
    out, raw = [], {}
    for sym in ("BTCUSDT", "ETHUSDT", "BNBUSDT"):
        k = klines(sym, "1d", 80)[:-1]                                   # closed daily candles only
        c = np.array([r["close"] for r in k])
        r20 = c[-1] / c[-21] - 1
        vol = np.std(np.diff(c[-31:]) / c[-31:-1], ddof=1) * np.sqrt(365)
        w = min(0.40 / vol, 2.0) / 3 if r20 > 0 else 0.0
        raw[sym] = w
        # price level where the signal would flip tomorrow: close 20 days back (the day that becomes the reference)
        out.append({"symbol": sym, "close": c[-1], "ret20": r20 * 100, "vol30": vol * 100, "flip_level": c[-20],
                    "state": "LONG" if r20 > 0 else "FLAT", "decided": k[-1]["time"],
                    "history": [{"time": r["time"], "value": r["close"]} for r in k]})
    g = sum(raw.values())
    for o in out:
        o["weight"] = (raw[o["symbol"]] / g if g > 1 else raw[o["symbol"]]) * 100
    return out


def _best(d: dict) -> dict:
    """Pull the headline numbers out of the differently shaped F*.json files."""
    if "chosen" in d and isinstance(d.get("grid"), dict) and d["chosen"] in d["grid"]:
        g = d["grid"][d["chosen"]]
        return g.get("base", g)
    for k in ("final", "valid", "base"):
        v = d.get(k)
        if isinstance(v, dict) and ("final" in v or "max_dd_pct" in v):
            return v
    return {}


def research():
    rows = []
    for line in (ROOT / "runs" / "ledger_c.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        b = r["result"].get("book", {})
        rows.append({"family": r["family"], "protocol": "C", "tf": r["tf"], "stage": r["stage"], "verdict": r["verdict"],
                     "final": b.get("final"), "pf": b.get("pf"), "dd": b.get("max_dd_pct"), "trades": b.get("trades"),
                     "sharpe": b.get("sharpe"), "twin": r["result"].get("twin_pct"),
                     "pf_x2": (r["result"].get("book_x2") or {}).get("pf"), "at": r["at"]})
    for f in sorted((ROOT / "runs").glob("F*_*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        b = _best(d)
        rows.append({"family": d.get("family", f.stem.split("_")[0]), "protocol": "F", "tf": "8h",
                     "stage": d.get("stage", f.stem.split("_")[-1]), "verdict": str(d.get("verdict", "")),
                     "final": b.get("final"), "pf": b.get("pf"), "dd": b.get("max_dd_pct"), "trades": b.get("trades"),
                     "sharpe": b.get("sharpe"), "twin": None, "pf_x2": None, "at": None})
    for name in ("C39_oi_gate.json", "C40_trend_gate.json"):
        p = ROOT / "runs" / name
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        if name.startswith("C40"):
            m = d["windows"]["RECENT"]["C40"]
            rows.append({"family": "C40", "protocol": "C", "tf": "1h", "stage": "recent", "verdict": d["decision"],
                         "final": m.get("final"), "pf": m.get("pf"), "dd": m.get("max_dd_pct"), "trades": m.get("trades"),
                         "sharpe": m.get("sharpe"), "twin": d["windows"]["RECENT"].get("C40_twin_pct"),
                         "pf_x2": (m.get("x2") or {}).get("pf"), "at": None})
        else:
            m = d["Validation"]["book"]
            rows.append({"family": "C39", "protocol": "C", "tf": "1h", "stage": "valid", "verdict": d["decision"],
                         "final": m.get("final"), "pf": m.get("pf"), "dd": m.get("max_dd_pct"), "trades": m.get("trades"),
                         "sharpe": m.get("sharpe"), "twin": d["Validation"].get("twin_pct"), "pf_x2": None, "at": None})
    return rows


def signals(symbol: str):
    """Every trigger of the scanner's 13 conditions on this coin's last ~187 days of 1h candles, with the
    playbook direction/badge and how each trade ended (same rule as the casebook: entry next open,
    target/stop in sigma24 units, stop counts first if both are hit in one bar, exit at the time limit)."""
    key = f"signals:{symbol}"
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < 120:
            return hit[1]
    import pandas as pd
    if str(OPP) not in sys.path:
        sys.path.insert(0, str(OPP))
    import common as OC                                          # research/opportunity/common.py
    book = json.loads((OPP / "playbook.json").read_text(encoding="utf-8"))["conditions"]
    if (OPP / "badges.json").exists():                           # effective badge: dev -> forward test
        eff = json.loads((OPP / "badges.json").read_text(encoding="utf-8"))["conditions"]
        book = {k: {**v, "badge": eff.get(k, {}).get("badge", v["badge"])} for k, v in book.items()}
    rows, end = [], None
    for _ in range(3):                                           # 3 pages x 1500 = 4500 hours
        q = f"/fapi/v1/klines?symbol={symbol}&interval=1h&limit=1500" + (f"&endTime={end}" if end else "")
        k = fetch(q, ttl=120)
        if not k:
            break
        rows = k + rows
        end = k[0][0] - 1
        if len(k) < 1500:
            break
    df = pd.DataFrame([{"date": pd.Timestamp(r[0], unit="ms", tz="UTC"), "open": float(r[1]), "high": float(r[2]),
                        "low": float(r[3]), "close": float(r[4]), "volume": float(r[5])} for r in rows])
    now = pd.Timestamp.now(tz="UTC")
    df = df[df["date"] + pd.Timedelta(hours=1) <= now]            # closed candles only
    f = fetch(f"/fapi/v1/fundingRate?symbol={symbol}&limit=1000", ttl=300)
    fund = pd.DataFrame([{"date": pd.Timestamp(r["fundingTime"], unit="ms", tz="UTC"), "funding_rate": float(r["fundingRate"])} for r in f])
    x = OC.compute_conditions(OC.regular_grid(df), fund)
    o, h, l, c = (x[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    t = np.array([int(d.timestamp()) for d in x["date"]])
    out, n = [], len(x)
    for name, rule in book.items():
        if name not in x:
            continue
        d = 1 if rule["direction"] == "LONG" else -1
        for i in OC.triggers(x[name]):
            if i + 1 >= n:
                entry, e_t = c[i], t[i] + 3600                   # triggered on the last closed bar: entry is the next open
            else:
                entry, e_t = o[i + 1], t[i + 1]
            sig = float(x["sigma24"].iloc[i])
            tp, sp = rule["target_sigma"] * sig, rule["stop_sigma"] * sig
            target, stop = entry * (1 + d * tp), entry * (1 - d * sp)
            res, ret, exit_t = "open", None, None
            for j in range(i + 1, min(i + 1 + rule["hours"], n)):
                adv = (stop >= l[j]) if d == 1 else (stop <= h[j])
                fav = (target <= h[j]) if d == 1 else (target >= l[j])
                if adv:
                    res, ret, exit_t = "stop", -sp, t[j]
                    break
                if fav:
                    res, ret, exit_t = "target", tp, t[j]
                    break
            else:
                if i + rule["hours"] < n:
                    j = i + rule["hours"]
                    res, ret, exit_t = "time", d * (c[j] / entry - 1), t[j]
            out.append({"time": int(t[i]), "entry_time": int(e_t), "condition": name, "why": rule["description"],
                        "direction": rule["direction"], "badge": rule["badge"], "entry": entry, "target": target,
                        "stop": stop, "hours": rule["hours"], "result": res,
                        "ret_pct": None if ret is None else round((ret - OC.COST_RT) * 100, 2), "exit_time": exit_t,
                        "test_avg_pct": rule["test"]["avg_net_pct"], "test_n": rule["test"]["n"]})
    out.sort(key=lambda s: s["time"])
    res = {"symbol": symbol, "from": int(t[0]), "to": int(t[-1]), "signals": out}
    with _lock:
        _cache[key] = (time.time(), res)
    return res


def forward():
    """Forward-test scoreboard (research/opportunity/forward.db + badges.json), read-only."""
    import sqlite3
    out = {"badges": None, "recent": [], "task": None}
    if (OPP / "badges.json").exists():
        out["badges"] = json.loads((OPP / "badges.json").read_text(encoding="utf-8"))
    db = OPP / "forward.db"
    if db.exists():
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=10)
        c.row_factory = sqlite3.Row
        out["recent"] = [dict(r) for r in c.execute("SELECT a.*, (SELECT COUNT(*) FROM alerts b WHERE b.condition = a.condition "
                                                    "AND b.trigger_time = a.trigger_time) cluster_n "
                                                    "FROM alerts a ORDER BY trigger_time DESC, id DESC LIMIT 150")]
        out["totals"] = dict(c.execute("SELECT COUNT(*) n, SUM(status IN ('open','pending')) open, "
                                       "SUM(status IN ('target','stop','time')) closed FROM alerts").fetchone())
        now = int(time.time())                     # the scanner's own verdicts, by when they were decided
        out["verdicts"] = {h: dict(c.execute("SELECT SUM(status='target') target, SUM(status='stop') stop, "
                                             "SUM(status='time') time FROM alerts WHERE exit_time >= ?",
                                             (now - h * 3600,)).fetchone()) for h in (24, 168)}
        out["books"] = paper_books(c)
        c.close()
    log = OPP / "scan_auto.log"
    if log.exists():
        runs = [l for l in log.read_text(encoding="utf-8", errors="replace").splitlines() if l.startswith("##### auto scan")]
        out["task"] = {"last_auto": runs[-1].replace("##### auto scan ", "") if runs else None, "auto_runs": len(runs)}
    return out


def paper_books(c) -> list[dict]:
    """Paper books (research/opportunity/paper_books.json): fixed rule sets traded on paper from their start, 50 USDT
    margin at 3x per signal, results straight from the forward log. Read-only."""
    import datetime
    f = OPP / "paper_books.json"
    if not f.exists():
        return []
    out = []
    for b in json.loads(f.read_text(encoding="utf-8"))["books"]:
        start = int(datetime.datetime.fromisoformat(b["start"].replace("Z", "+00:00")).timestamp())
        rows = [dict(r) for r in c.execute(
            "SELECT a.*, (SELECT COUNT(*) FROM alerts x WHERE x.condition = a.condition AND x.trigger_time = a.trigger_time) cluster_n "
            "FROM alerts a WHERE a.trigger_time >= ? ORDER BY a.trigger_time DESC, a.id DESC", (start,))]
        rows = [r for r in rows if (not b["rules"] or r["condition"] in b["rules"])
                and (not b["max_cluster"] or r["cluster_n"] <= b["max_cluster"])]
        pos = b["margin_usdt"] * b["leverage"]
        for r in rows:
            r["usdt"] = None if r["ret_pct"] is None else round(max(pos * r["ret_pct"] / 100, -b["margin_usdt"]), 2)
        closed = [r for r in rows if r["status"] in ("target", "stop", "time")]
        n = lambda s: sum(r["status"] == s for r in closed)
        out.append({**b, "trades": rows[:100], "closed": len(closed), "open": sum(r["status"] in ("open", "pending") for r in rows),
                    "target": n("target"), "stop": n("stop"), "time": n("time"),
                    "net_usdt": round(sum(r["usdt"] for r in closed), 2), "days": len({r["exit_time"] // 86400 for r in closed})})
    return out


def postmortem():
    """Why scanner signals passed/failed + changes checked on history (research/opportunity/postmortem.json), read-only."""
    f = OPP / "postmortem.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def incubator():
    """Strategy incubator state (research/incubator/state.json, REPORT_latest.md, discovery_log.md), read-only."""
    inc = RES / "incubator"
    out = {"state": None, "report": None, "discovery": None}
    if (inc / "state.json").exists():
        out["state"] = json.loads((inc / "state.json").read_text(encoding="utf-8"))
    if (inc / "discovery_log.md").exists():
        out["discovery"] = (inc / "discovery_log.md").read_text(encoding="utf-8")[-6000:]
    return out


def bear_lab():
    """Bear lab (research/bear_lab/bear_lab.db, state.json, discovery_log.md), read-only: ideas on paper with their
    history screen and latest live evaluation, screen counts, discovery log tail."""
    import sqlite3
    lab = RES / "bear_lab"
    out = {"ideas": [], "screens": {"total": 0, "passed": 0}, "state": None, "discovery": None,
           "passed_md": (lab / "PASSED.md").read_text(encoding="utf-8") if (lab / "PASSED.md").exists() else None}
    if (lab / "state.json").exists():
        out["state"] = json.loads((lab / "state.json").read_text(encoding="utf-8"))
    if (lab / "discovery_log.md").exists():
        out["discovery"] = (lab / "discovery_log.md").read_text(encoding="utf-8")[-8000:]
    if not (lab / "bear_lab.db").exists():
        return out
    c = sqlite3.connect(f"file:{(lab / 'bear_lab.db').as_posix()}?mode=ro", uri=True, timeout=10)
    try:
        out["screens"] = dict(zip(("total", "passed"), c.execute("SELECT COUNT(*), COALESCE(SUM(passed), 0) FROM screens").fetchone()))
        for iid, src, reason, start, status, why, screen in c.execute(
                "SELECT id, source, reason, start_ts, status, status_why, screen FROM ideas ORDER BY start_ts"):
            ev = c.execute("SELECT ts, stats FROM evals WHERE id=? ORDER BY ts DESC LIMIT 1", (iid,)).fetchone()
            out["ideas"].append({"id": iid, "source": src, "reason": reason, "start": start, "status": status, "why": why,
                                 "screen": json.loads(screen or "{}"), "eval_ts": ev[0] if ev else None,
                                 "live": json.loads(ev[1]) if ev else {}})
    finally:
        c.close()
    return out


def v4_forward():
    """V4 complacency-short forward test (research/fresh/forward_v4/state.json, hourly task), read-only."""
    f = RES / "fresh" / "forward_v4" / "state.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"missing": True}


def market_fit():
    """Market-condition scanner (research/fresh/regime_scan.py now): today's market type and what NFI and
    E0V1EN did in that type over their 30-month backtests. Information only. Re-run at most hourly (via swr)."""
    py, script = PY, RES / "fresh" / "regime_scan.py"
    r = subprocess.run([str(py), str(script), "now"], cwd=str(ROOT), capture_output=True, text=True, timeout=300, creationflags=NO_WINDOW)
    f = RES / "fresh" / "regime_now.json"
    if r.returncode != 0 or not f.exists():
        raise RuntimeError(((r.stderr or r.stdout or "regime_scan failed").strip().splitlines() or ["regime_scan failed"])[-1])
    return json.loads(f.read_text(encoding="utf-8"))


def crashday_forward():
    """Crash-day forward log, Bear-Wild (research/fresh/forward_crash/state.json, hourly task), read-only.
    Adds the historical replay summary (reference only, not part of the verdict)."""
    d = RES / "fresh" / "forward_crash"
    f = d / "state.json"
    if not f.exists():
        return {"missing": True}
    out = json.loads(f.read_text(encoding="utf-8"))
    rp = d / "replay.json"
    if rp.exists():
        r = json.loads(rp.read_text(encoding="utf-8"))
        out["replay"] = {"from": r.get("from"), "summary": r.get("summary")}
    return out


def switcher():
    """Switcher paper bot (research/fresh/switcher_paper, hourly loop, public candles, no orders), read-only.
    Adds a health check: is the loop process alive and did the last pass run within the last 75 minutes."""
    d = RES / "fresh" / "switcher_paper"
    f = d / "status.json"
    if not f.exists():
        return {"missing": True}
    out = json.loads(f.read_text(encoding="utf-8"))
    pid, alive = None, False
    try:
        pid = int((d / "pid.txt").read_text(encoding="utf-8").strip())
        r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, timeout=10,
                           creationflags=NO_WINDOW)
        alive = str(pid) in r.stdout and "python" in r.stdout.lower()
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    age = None
    if out.get("checked_utc"):
        age = round((time.time() - __import__("calendar").timegm(time.strptime(out["checked_utc"], "%Y-%m-%d %H:%M:%S"))) / 60)
    log = d / "log.txt"
    tail = log.read_text(encoding="utf-8").splitlines()[-8:] if log.exists() else []
    errors = sum("ERROR" in x for x in tail)
    out["health"] = {"pid": pid, "alive": alive, "age_min": age, "errors_recent": errors,
                     "ok": bool(alive and age is not None and age <= 75 and errors == 0)}
    out["log"] = tail
    return out


def delist_paper():
    """Delisting-short paper bot (research/fresh/delist/paper.py, polls announcements each minute), read-only."""
    d = RES / "fresh" / "delist"
    f = d / "paper_state.json"
    if not f.exists():
        return {"missing": True}
    st = json.loads(f.read_text(encoding="utf-8"))
    alive = False
    try:
        pid = int((d / "paper_pid.txt").read_text(encoding="utf-8").strip())
        r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, timeout=10,
                           creationflags=NO_WINDOW)
        alive = str(pid) in r.stdout
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    age = None
    if st.get("checked_utc"):
        age = round((time.time() - __import__("calendar").timegm(time.strptime(st["checked_utc"], "%Y-%m-%d %H:%M:%S"))) / 60)
    log = d / "paper_log.txt"
    tail = log.read_text(encoding="utf-8").splitlines()[-6:] if log.exists() else []
    return {"open": st.get("open", []), "closed": st.get("closed", [])[-30:], "pending": st.get("pending", []),
            "health": {"alive": alive, "age_min": age, "ok": bool(alive and age is not None and age <= 5)}, "log": tail}


def insights_api(q: dict) -> dict:
    syms = [s for s in q.get("symbols", "").split(",") if s]
    sides = dict(x.split(":", 1) for x in q.get("sides", "").split(",") if ":" in x)
    return insights.build(fetch, syms, sides)


def scan_status():
    p = _scan["proc"]
    running = p is not None and p.poll() is None
    data = json.loads((OPP / "latest_scan.json").read_text(encoding="utf-8")) if (OPP / "latest_scan.json").exists() else None
    f1 = json.loads((OPP / "f1_alerts.json").read_text(encoding="utf-8")) if (OPP / "f1_alerts.json").exists() else None
    if f1:
        f1["history_n"] = len(f1.pop("history", []))
    return {"running": running, "started": _scan["started"], "scan": data, "f1": f1}


def scan_run():
    if _scan["proc"] is not None and _scan["proc"].poll() is None:
        return {"running": True}
    _scan["proc"] = subprocess.Popen([str(PY), str(OPP / "scan.py"), "--top", "200"],
                                     cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     creationflags=NO_WINDOW)
    _scan["started"] = time.time()
    return {"running": True}


# ------------------------------------------------------------------ http
class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(HERE / "static"), **kw)

    def log_message(self, *_):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, default=float).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def end_headers(self):
        if self.path.startswith("/vendor/"):
            self.send_header("Cache-Control", "max-age=86400")      # chart library never changes
        elif not self.path.startswith("/api/"):
            # no-cache = re-check (cheap 304), still picks up edits; no-store made the browser re-download every
            # file and throw the page away when the tab was left
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        sym = q.get("symbol", "BTCUSDT").upper()
        try:
            if u.path == "/vendor/lightweight-charts.js":
                b = (HERE / "vendor" / "lightweight-charts.js").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/javascript")
                self.end_headers()
                self.wfile.write(b)
                return
            routes = {
                "/api/tickers": lambda: tickers(),
                "/api/klines": lambda: klines(sym, q.get("interval", "1h"), int(q.get("limit", 1000))),
                "/api/funding": lambda: funding(sym),
                "/api/oi": lambda: oi(sym),
                "/api/majors": lambda: swr("t:majors", majors, 300),
                "/api/majors_equity": lambda: json.loads((ROOT / "data" / "ui_majors_equity.json").read_text(encoding="utf-8")),
                "/api/research": lambda: research(),
                "/api/scan": lambda: scan_status(),
                "/api/signals": lambda: swr(f"t:signals:{sym}", lambda: signals(sym), 120),
                "/api/forward": lambda: swr("t:forward", forward, 20),
                "/api/postmortem": lambda: postmortem(),
                "/api/incubator": lambda: incubator(),
                "/api/bearlab": lambda: bear_lab(),
                "/api/v4": lambda: v4_forward(),
                "/api/crashday": lambda: crashday_forward(),
                "/api/switcher": lambda: switcher(),
                "/api/delist": lambda: delist_paper(),
                "/api/fit": lambda: swr("t:fit", market_fit, 3600, max_stale=4 * 3600),
                "/api/trader": lambda: trader(),
                "/api/decisions": lambda: decisions.build(fetch),
                "/api/insights": lambda: insights_api(q),
                "/api/today": lambda: swr("t:today", _today, 30),
            }
            if u.path in routes:
                return self._json(routes[u.path]())
        except Exception as e:                                   # report, never crash the server
            return self._json({"error": f"{type(e).__name__}: {e}"}, 502)
        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/scan/run":
            return self._json(scan_run())
        if self.path in ("/api/trader/action", "/api/journal"):
            # Only this page may write: same-origin request with the custom header (another website's
            # script cannot add it without a CORS pre-flight, which this server never approves).
            origin = self.headers.get("Origin", "")
            if origin not in (f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}") or self.headers.get("X-Quantlab") != "1":
                return self._json({"error": "refused: not from the quantlab page"}, 403)
            n = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self._json({"error": "bad request"}, 400)
            with _lock:
                _cache.pop("t:today", None)                       # notes/decisions/actions show at once on Today
            if self.path == "/api/journal":
                try:
                    return self._json(today.add_note(str(body.get("text", "")), body.get("mood") or None))
                except ValueError as e:
                    return self._json({"error": str(e)}, 400)
            return self._json(trader_action(body))
        self._json({"error": "not found"}, 404)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    print(f"Quantlab UI on http://localhost:{port}", flush=True)
    threading.Thread(target=warm, daemon=True).start()
    # The browser opens "localhost" on IPv6 (::1) first; with nothing listening there Windows waits ~2 s before it
    # falls back to 127.0.0.1, on every new connection. So listen on both loopbacks (still this PC only).
    import socket

    class H6(ThreadingHTTPServer):
        address_family = socket.AF_INET6
    try:
        threading.Thread(target=H6(("::1", port), H).serve_forever, daemon=True).start()
    except OSError as e:
        print(f"IPv6 loopback not available ({e}); localhost may be slow", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
