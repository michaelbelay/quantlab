"""Scalp lab: bear-day scalps on 5m candles -> screen -> live scalp alerts + paper on live data -> verdict on new data only.
Rules: research/scalp_lab/SCALP_LAB.md.

  .venv\\Scripts\\python.exe research\\scalp_lab\\scalp_lab.py screen research/scalp_lab/ideas/X.py
  .venv\\Scripts\\python.exe research\\scalp_lab\\scalp_lab.py add research/scalp_lab/ideas/X.py --source "main 2026-11-06"
  .venv\\Scripts\\python.exe research\\scalp_lab\\scalp_lab.py scan          # every 5 min: live candles, alerts, paper, verdicts
  .venv\\Scripts\\python.exe research\\scalp_lab\\scalp_lab.py report
  .venv\\Scripts\\python.exe research\\scalp_lab\\scalp_lab.py list

An idea is one file in ideas/ (frozen by sha256 when it enters):
  SIDE = 1 or -1                 long or short
  HOLD = 24                      max 5m bars in the trade (1..48 = 4h)
  UNIT = "atr"                   "atr": STOP/TARGET are multiples of the 14-bar ATR at the signal; "pct": fractions
  STOP = 1.5                     hard stop (checked first inside a candle)
  TARGET = 1.5                   take-profit, or None
  GAP = 12                       min bars between two entries of the same coin
  REASON = "..."                 one line: who is forced to trade, why it repeats
  def signals(P) -> DataFrame[bool] (5m bars x coins), True on the closed bar where the trade is entered at its close.
  Signals may look back at most WARMUP bars (2000 = ~7 days); the live panel holds no more than that before the start.
The engine itself adds: bear day (BTC 20-day return <= 0 at the last daily close, same rule as the bear lab), 10M USDT
24h volume, one trade per coin at a time, 0.14% round trip, real funding. P keys: see panels().
"""
from __future__ import annotations

import argparse
import hashlib
import math
import importlib.util
import json
import sqlite3
import sys
import time
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IDEAS = HERE / "ideas"
DB = HERE / "scalp_lab.db"
STATE = HERE / "state.json"
LATEST = HERE / "latest_scalps.json"
LIVE5 = HERE / "live_5m"
LOCK = HERE / "scan.lock"
FUT = ROOT / "data" / "market" / "main" / "binance" / "futures"
LIVE1H = ROOT / "research" / "opportunity" / "live_cache"
COINS = ["BTC", "ETH", "ZEC", "SOL", "XRP", "HYPE", "NEAR", "DOGE", "UNI", "BNB", "SUI", "ENA", "QNT", "ARB", "WLD",
         "PUMP", "LINK", "ADA", "TAO"]                      # same 19 as the bear lab (trader COINS minus 1000PEPE)
BAR = pd.Timedelta(minutes=5)
START = pd.Timestamp("2024-02-01", tz="UTC")                # first 5m history bar
HIST_END = pd.Timestamp("2026-10-01", tz="UTC")             # screen window end (history files)
MID = pd.Timestamp("2025-06-01", tz="UTC")                  # halves A / B
WARMUP = 2000
COST = 0.0014                                               # taker 0.05% x 2 + 0.02% slippage x 2
SCREEN = {"min_trades": 200, "min_trades_half": 60, "min_avg_half": 0.0, "min_avg_2x": 0.0}
VERDICT = {"min_trades": 60, "min_days": 10, "min_t": 2.5, "max_days": 120}
MAX_ADD_PER_DAY = 3
ICON = {"PAPER": "🧪", "PASS": "🟡", "KILLED": "🔴", "EXPIRED": "⚪", "TAMPERED": "⛔"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    return pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")


def db() -> sqlite3.Connection:
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE IF NOT EXISTS ideas (id TEXT PRIMARY KEY, file TEXT, sha TEXT, code_sha TEXT, source TEXT, reason TEXT,
      entered TEXT, start_ts TEXT, status TEXT, status_why TEXT, screen TEXT, updated TEXT);
    CREATE TABLE IF NOT EXISTS screens (ts TEXT, file TEXT, sha TEXT, passed INTEGER, result TEXT);
    CREATE TABLE IF NOT EXISTS evals (ts TEXT, id TEXT, stats TEXT);
    CREATE TABLE IF NOT EXISTS alerts (id TEXT, coin TEXT, entry TEXT, sent TEXT, alert TEXT, PRIMARY KEY (id, coin, entry));""")
    return c


def load_idea(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------- data
def _read(p: Path) -> pd.DataFrame:
    d = pd.read_feather(p)
    d["date"] = pd.to_datetime(d["date"], utc=True)
    return d


def _candles(c: str, a: pd.Timestamp) -> pd.DataFrame:
    parts = []
    f = FUT / f"{c}_USDT_USDT-5m-futures.feather"
    if f.exists() and a < HIST_END:
        d = _read(f)
        parts.append(d[d.date >= a])
    lf = LIVE5 / f"{c}.feather"
    if lf.exists():
        parts.append(_read(lf))
    d = pd.concat(parts).drop_duplicates("date", keep="last").set_index("date").sort_index()
    return d[["open", "high", "low", "close", "volume"]]


def _funding(c: str) -> pd.Series:
    parts = []
    f = FUT / f"{c}_USDT_USDT-1h-funding_rate.feather"
    if f.exists():
        parts.append(_read(f)[["date", "funding_rate"]])
    lf = LIVE1H / f"{c}USDT_funding.feather"
    if lf.exists():
        parts.append(_read(lf)[["date", "funding_rate"]])
    d = pd.concat(parts)
    d["date"] = d["date"].dt.round("5min")
    return d.drop_duplicates("date", keep="last").set_index("date").sort_index().funding_rate


def atr(P: dict, n: int = 14) -> pd.DataFrame:
    pc = P["C"].shift(1)
    tr = np.maximum(P["H"] - P["L"], np.maximum((P["H"] - pc).abs(), (P["L"] - pc).abs()))
    return tr.rolling(n, min_periods=n).mean()


def panels(a: pd.Timestamp = START, b: pd.Timestamp | None = None) -> dict:
    """all inputs on one 5m grid [a, b). Index = bar open time; values known at the bar close."""
    a = max(a, START)
    raw = {c: _candles(c, a) for c in COINS}
    last = raw["BTC"].index.max()
    if b is not None:
        last = min(last, b - BAR)
    last = min(last, pd.Timestamp.now(tz="UTC").floor("5min") - BAR)      # closed bars only
    X = pd.date_range(a, last, freq="5min")
    P = {k: pd.DataFrame({c: raw[c][col].reindex(X) for c in COINS}) for k, col in
         (("O", "open"), ("H", "high"), ("L", "low"), ("C", "close"), ("V", "volume"))}
    P["QV"] = P["C"] * P["V"]
    T = X + BAR
    P["FUND"] = pd.DataFrame({c: _funding(c).reindex(T).to_numpy() for c in COINS}, index=X)   # settled at bar close
    P["FUND_LAST"] = P["FUND"].ffill()
    P["ATR"] = atr(P)
    P["ELIG"] = (P["QV"].rolling(288, min_periods=288).sum() >= 1e7) & P["C"].notna()
    # bear day (bear lab rule): BTC daily close = close of the 23:55 bar; day d is bear if close(d-1) / close(d-21) <= 1.
    # History before a is read from the 1h file so the flag is known from the first bar.
    btc1h = _read(FUT / "BTC_USDT_USDT-1h-futures.feather").set_index("date").close
    lf = LIVE1H / "BTCUSDT_1h.feather"
    if lf.exists():
        btc1h = pd.concat([btc1h, _read(lf).set_index("date").close])
    btc1h = btc1h[~btc1h.index.duplicated(keep="last")].sort_index()
    dc = btc1h[btc1h.index.hour == 23]
    dc.index = dc.index.normalize() + pd.Timedelta(days=1)
    b5 = P["C"]["BTC"]
    d5 = b5[(b5.index.hour == 23) & (b5.index.minute == 55)].dropna()
    d5.index = d5.index.normalize() + pd.Timedelta(days=1)
    dc = pd.concat([dc[~dc.index.isin(d5.index)], d5]).sort_index()
    bear_day = (dc / dc.shift(20) - 1 <= 0)
    entry_day = T.normalize()                                    # the trade starts at the bar close
    P["BEAR"] = pd.Series(entry_day.map(bear_day).fillna(False).astype(bool), index=X)
    P["INDEX"] = X
    P["COINS"] = COINS
    return P


# helpers for idea files
def ema(df: pd.DataFrame, n: int) -> pd.DataFrame:
    return df.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(df: pd.DataFrame, n: int) -> pd.DataFrame:
    d = df.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn)


def vwap(P: dict, n: int = 288) -> pd.DataFrame:
    tp = (P["H"] + P["L"] + P["C"]) / 3
    return (tp * P["V"]).rolling(n, min_periods=n).sum() / P["V"].rolling(n, min_periods=n).sum()


# ---------------------------------------------------------------- engine
def trades(m, P: dict, a: pd.Timestamp, b: pd.Timestamp, include_open=False) -> pd.DataFrame:
    """trades entered in [a, b). Engine rules are fixed here, not in the idea."""
    X = P["INDEX"]
    sig = m.signals(P)
    sig = sig.reindex(index=X, columns=COINS).fillna(False).astype(bool).to_numpy()
    base = sig & P["ELIG"].to_numpy() & P["BEAR"].to_numpy()[:, None]
    ok = np.asarray((X >= a) & (X < b))
    CL, HI, LO, AT = P["C"].to_numpy(), P["H"].to_numpy(), P["L"].to_numpy(), P["ATR"].to_numpy()
    CF = P["FUND"].fillna(0).cumsum().to_numpy()
    side, hold, gap = int(m.SIDE), int(m.HOLD), int(getattr(m, "GAP", 0))
    unit, stop, target = getattr(m, "UNIT", "pct"), float(m.STOP), getattr(m, "TARGET", None)
    n = len(X)
    rows = []
    for k, c in enumerate(COINS):
        busy, last_e = -1, -10 ** 9
        for i in np.flatnonzero(base[:, k] & ok):
            if i <= busy or i - last_e < gap or np.isnan(CL[i, k]):
                continue
            e = CL[i, k]
            if unit == "atr":
                if np.isnan(AT[i, k]) or AT[i, k] <= 0:
                    continue
                sd, td = stop * AT[i, k] / e, (target * AT[i, k] / e if target else None)
            else:
                sd, td = stop, target
            sp = e * (1 - side * sd)
            tp = e * (1 + side * td) if td else None
            end = min(i + hold, n - 1)
            seg = slice(i + 1, end + 1)
            cl, hi, lo = CL[seg, k], HI[seg, k], LO[seg, k]
            gaps = np.flatnonzero(np.isnan(cl))
            lim = gaps[0] if len(gaps) else len(cl)
            hit_s = (lo[:lim] <= sp) if side == 1 else (hi[:lim] >= sp)
            hit_t = ((hi[:lim] >= tp) if side == 1 else (lo[:lim] <= tp)) if tp is not None else np.zeros(lim, bool)
            hs = np.flatnonzero(hit_s)
            ht = np.flatnonzero(hit_t)
            s0 = hs[0] if len(hs) else 10 ** 9
            t0 = ht[0] if len(ht) else 10 ** 9
            j = None
            if s0 <= t0 and s0 < 10 ** 9:
                j, px, why = i + 1 + s0, sp, "stop"                         # same candle: the stop counts
            elif t0 < 10 ** 9:
                j, px, why = i + 1 + t0, tp, "target"
            elif lim < len(cl):
                j, px, why = i + lim, CL[i + lim, k], "gap"
            elif i + hold <= n - 1:
                j, px, why = i + hold, CL[i + hold, k], "time"
            is_open = j is None
            if is_open:
                if not include_open:
                    busy = n
                    continue
                j, px, why = n - 1, CL[n - 1, k], "open"
            if j <= i and not is_open:
                continue
            g = side * (px / e - 1) - side * (CF[j, k] - CF[i, k])            # longs pay positive funding
            rows.append((c, X[i] + BAR, X[j] + BAR, why, e, sp, tp, g - COST, g - 2 * COST))
            busy, last_e = (n if is_open else j), i
    return pd.DataFrame(rows, columns=["coin", "entry", "exit", "why", "entry_px", "stop_px", "target_px", "net", "net2x"])



def day_t(d: "pd.Series") -> float:
    """t of the daily means against zero, capped by what the NUMBER of winning days alone can establish.

    Why the cap (2026-11-13): an idea with a fixed take-profit returns the same percentage on every win, so while
    a run has no losing trade yet the spread of the daily means is about zero and the plain t explodes.
    cdeep_funding_take reached t = 1713 on 7 trades that were all exactly +4.8%, and t = 548 the next day - with
    min_t = 2.5 the verdict gate would have waved it through on arithmetic, not on evidence. The sign test ignores
    how big the wins are and asks only how many independent days came out positive, which is the most a sample
    this size can prove when every trade pays the same. The reported t is the smaller of the two.
    """
    n = len(d)
    if n < 2:
        return 0.0
    sd = float(d.std(ddof=1))
    mean = float(d.mean())
    t = (mean / sd * np.sqrt(n)) if sd > 0 else float("inf")
    if mean <= 0:                                     # a losing idea: the plain t already fails the gate
        return round(t, 2) if sd > 0 else 0.0
    wins = int((d > 0).sum())
    p = sum(math.comb(n, k) for k in range(wins, n + 1)) / 2 ** n       # one-sided sign test on the daily means
    z = NormalDist().inv_cdf(1 - min(max(p, 1e-12), 1 - 1e-12))
    return round(min(t, z), 2)

def summarize(tr: pd.DataFrame) -> dict:
    if tr.empty:
        return {"trades": 0}
    d = tr.groupby(tr.entry.dt.normalize()).net.mean()
    t = day_t(d)
    a, b = tr[tr.entry < MID], tr[tr.entry >= MID]
    return {"trades": len(tr), "days": len(d), "avg": round(100 * tr.net.mean(), 3), "avg_2x": round(100 * tr.net2x.mean(), 3),
            "day_avg": round(100 * d.mean(), 3), "day_t": round(t, 2), "win": round(100 * (tr.net > 0).mean(), 1),
            "trades_A": len(a), "avg_A": round(100 * a.net.mean(), 3) if len(a) else None,
            "trades_B": len(b), "avg_B": round(100 * b.net.mean(), 3) if len(b) else None,
            "sum_pct": round(100 * tr.net.sum(), 1), "exits": tr.why.value_counts().to_dict(),
            "worst": [(r.coin, str(r.entry)[:16], round(100 * r.net, 2)) for r in tr.nsmallest(3, "net").itertuples()]}


# ---------------------------------------------------------------- commands
def code_sha() -> str:
    return sha(Path(__file__))


def check_idea_file(path: Path):
    m = load_idea(path)
    assert getattr(m, "SIDE", None) in (1, -1), "SIDE must be 1 or -1"
    for k in ("HOLD", "STOP", "REASON", "signals"):
        assert hasattr(m, k), f"missing {k}"
    unit = getattr(m, "UNIT", "pct")
    assert unit in ("atr", "pct"), "UNIT is 'atr' or 'pct'"
    assert 1 <= m.HOLD <= 48, "HOLD 1..48 bars (4h)"
    assert (0.3 <= m.STOP <= 6) if unit == "atr" else (0.002 <= m.STOP <= 0.05), "STOP 0.3..6 ATR or 0.2%..5%"
    src = path.read_text(encoding="utf-8")
    for bad in ("shift(-", ".shift(periods=-", "bfill", "backfill", "center=True", "requests", "urllib", "ccxt", "open("):
        assert bad not in src, f"not allowed in an idea: {bad}"
    return m


def cmd_screen(path: Path) -> dict:
    m = check_idea_file(path)
    P = panels(START, HIST_END)
    tr = trades(m, P, START, HIST_END)
    s = summarize(tr)
    ok = (s.get("trades", 0) >= SCREEN["min_trades"] and s["trades_A"] >= SCREEN["min_trades_half"]
          and s["trades_B"] >= SCREEN["min_trades_half"] and (s["avg_A"] or -1) > SCREEN["min_avg_half"]
          and (s["avg_B"] or -1) > SCREEN["min_avg_half"] and s["avg_2x"] > SCREEN["min_avg_2x"])
    s["passed"] = bool(ok)
    with db() as c:
        c.execute("INSERT INTO screens VALUES (?,?,?,?,?)", (now(), str(path.as_posix()), sha(path), int(ok), json.dumps(s)))
        s["screens_so_far"] = c.execute("SELECT COUNT(*) FROM screens").fetchone()[0]
    print(json.dumps(s, ensure_ascii=False))
    return s


def cmd_add(path: Path, source: str):
    h = sha(path)
    with db() as c:
        row = c.execute("SELECT result FROM screens WHERE sha=? AND passed=1 ORDER BY ts DESC", (h,)).fetchone()
        if row is None:
            sys.exit("not added: this exact file has no passed screen")
        today = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
        if c.execute("SELECT COUNT(*) FROM ideas WHERE substr(entered,1,10)=?", (today,)).fetchone()[0] >= MAX_ADD_PER_DAY:
            sys.exit(f"not added: {MAX_ADD_PER_DAY} ideas already entered today")
        iid = path.stem
        if c.execute("SELECT 1 FROM ideas WHERE id=?", (iid,)).fetchone():
            sys.exit("not added: an idea with this name exists (a changed idea needs a new file name)")
        m = load_idea(path)
        start = pd.Timestamp.now(tz="UTC").floor("5min")
        c.execute("INSERT INTO ideas VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (iid, str(path.relative_to(ROOT).as_posix()), h, code_sha(), source, m.REASON, now(), start.isoformat(),
                   "PAPER", "", row[0], now()))
    print(f"added {iid}: live alerts + paper from {start} UTC")


def update_live():
    """closed 5m candles for the 19 coins since the history end, Binance public data (no key)."""
    import ccxt
    LIVE5.mkdir(exist_ok=True)
    ex = ccxt.binanceusdm({"enableRateLimit": True})
    now_ms = int(time.time() * 1000)
    for c in COINS:
        f = LIVE5 / f"{c}.feather"
        old = _read(f) if f.exists() else None
        since = (int(old["date"].iloc[-1].timestamp() * 1000) if old is not None and len(old)
                 else int((HIST_END - pd.Timedelta(days=1)).timestamp() * 1000))
        got = []
        while since < now_ms - 300_000:
            b = ex.fetch_ohlcv(f"{c}/USDT:USDT", "5m", since=since, limit=1500)
            if not b:
                break
            got += b
            if b[-1][0] + 300_000 <= since:
                break
            since = b[-1][0] + 300_000
        new = pd.DataFrame(got, columns=["ts", "open", "high", "low", "close", "volume"])
        new["date"] = pd.to_datetime(new["ts"], unit="ms", utc=True)
        d = pd.concat([old, new.drop(columns="ts")]) if old is not None else new.drop(columns="ts")
        d = d.drop_duplicates("date", keep="last").sort_values("date")
        d = d[d["date"] + BAR <= pd.Timestamp.now(tz="UTC")].reset_index(drop=True)      # closed bars only
        d["date"] = d["date"].astype("datetime64[ns, UTC]")
        d.to_feather(f)


def notify(title: str, body: str):
    try:
        sys.path.insert(0, str(ROOT / "research" / "opportunity"))
        import forward as FW
        FW.notify(title, body)
    except Exception:
        pass


def _fmt(px: float) -> str:
    return f"{px:.6g}"


def cmd_scan(update=True):
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime < 600:
        print("another scan is running")
        return
    LOCK.write_text(now())
    try:
        if update:
            update_live()
        with db() as c:
            rows = c.execute("SELECT * FROM ideas WHERE status IN ('PAPER','PASS')").fetchall()
        live = {"ts": now(), "data_until": None, "bear_day": None, "open": [], "new_alerts": [], "ideas": []}
        if not rows:
            P = panels(pd.Timestamp.now(tz="UTC").floor("5min") - 400 * BAR)
            live["data_until"], live["bear_day"] = str(P["INDEX"][-1] + BAR), bool(P["BEAR"].iloc[-1])
        else:
            first = min(pd.Timestamp(r["start_ts"]) for r in rows)
            P = panels(first - WARMUP * BAR)
            X = P["INDEX"]
            end = X[-1] + BAR
            live["data_until"] = str(end)
            live["bear_day"] = bool(P["BEAR"].iloc[-1])
            out = {"ts": now(), "data_until": str(end), "ideas": []}
            with db() as c:
                for r in rows:
                    p = ROOT / r["file"]
                    if not p.exists() or sha(p) != r["sha"] or r["code_sha"] != code_sha():
                        c.execute("UPDATE ideas SET status='TAMPERED', status_why=?, updated=? WHERE id=?",
                                  ("idea file or scalp_lab.py changed after entry", now(), r["id"]))
                        continue
                    m = load_idea(p)
                    start = pd.Timestamp(r["start_ts"])
                    allt = trades(m, P, start - BAR, end, include_open=True)    # entry = signal bar close >= start
                    allt = allt[allt.entry >= start]
                    closed, opened = allt[allt.why != "open"], allt[allt.why == "open"]
                    s = summarize(closed)
                    side = "LONG" if m.SIDE == 1 else "SHORT"
                    for x in opened.itertuples():
                        o = {"idea": r["id"], "status": r["status"], "coin": x.coin, "side": side,
                             "entry_time": str(x.entry), "entry": _fmt(x.entry_px), "stop": _fmt(x.stop_px),
                             "target": _fmt(x.target_px) if x.target_px == x.target_px and x.target_px else None,
                             "exit_by": str(x.entry + int(m.HOLD) * BAR), "now_pct": round(100 * x.net, 2)}
                        live["open"].append(o)
                        if c.execute("INSERT OR IGNORE INTO alerts VALUES (?,?,?,?,?)",
                                     (r["id"], x.coin, str(x.entry), now(), json.dumps(o))).rowcount:
                            if x.entry >= end - 2 * BAR:                       # fresh only; no toasts for old catch-up
                                live["new_alerts"].append(o)
                    s["open"] = [(x.coin, str(x.entry)[:16], round(100 * x.net, 2)) for x in opened.itertuples()]
                    age = (end - start).days
                    status, why = r["status"], r["status_why"]
                    if status == "PAPER":
                        if s.get("trades", 0) >= VERDICT["min_trades"] and s["days"] >= VERDICT["min_days"]:
                            if s["day_avg"] <= 0:
                                status, why = "KILLED", f"day average {s['day_avg']}% <= 0 after {s['trades']} trades"
                            elif s["day_t"] >= VERDICT["min_t"] and s["avg_2x"] > 0:
                                status, why = "PASS", f"{s['trades']} trades on {s['days']} days, day avg {s['day_avg']}%, t {s['day_t']}"
                        if status == "PAPER" and age >= VERDICT["max_days"]:
                            status, why = "EXPIRED", f"no verdict after {age} days"
                    elif status == "PASS" and s.get("day_avg", 0) <= 0:
                        status, why = "KILLED", f"after PASS: day average {s['day_avg']}% <= 0"
                    if status != r["status"]:
                        c.execute("UPDATE ideas SET status=?, status_why=?, updated=? WHERE id=?", (status, why, now(), r["id"]))
                        if status == "PASS":
                            notify("Scalp lab: rule PASSED on live data", f"{r['id']}: {why}")
                            with open(HERE / "PASSED.md", "a", encoding="utf-8") as fh:
                                fh.write(f"- {now()} {r['id']}: {why}. Worst closed: {s['worst']}\n")
                    out["ideas"].append({"id": r["id"], "status": status, "why": why, "age_days": age, "side": side,
                                         "hold_bars": int(m.HOLD), **s})
                if pd.Timestamp.now(tz="UTC").minute < 5:
                    for x in out["ideas"]:
                        c.execute("INSERT INTO evals VALUES (?,?,?)", (now(), x["id"], json.dumps(x, default=str)))
            STATE.write_text(json.dumps(out, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
            live["ideas"] = [{k: x.get(k) for k in ("id", "status", "side", "trades", "days", "avg", "day_t")} for x in out["ideas"]]
        for o in live["new_alerts"]:
            tgt = f" target {o['target']}" if o["target"] else ""
            notify(f"Scalp {o['side']} {o['coin']} ({o['idea']}, paper rule)",
                   f"entry {o['entry']} stop {o['stop']}{tgt} exit by {o['exit_by'][11:16]} UTC")
        LATEST.write_text(json.dumps(live, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
        print(f"{now()} scan: {len(rows)} rules, {len(live['open'])} open scalps, {len(live['new_alerts'])} new alerts, "
              f"bear day {live['bear_day']}, data until {live['data_until']}")
        cmd_report(quiet=True)
    finally:
        LOCK.unlink(missing_ok=True)


def cmd_report(quiet=False):
    with db() as c:
        ideas = c.execute("SELECT id, status, status_why, entered, start_ts, reason FROM ideas ORDER BY entered").fetchall()
        n_screens = c.execute("SELECT COUNT(*) FROM screens").fetchone()[0]
        n_pass = c.execute("SELECT COUNT(*) FROM screens WHERE passed=1").fetchone()[0]
    st = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"ideas": []}
    lv = json.loads(LATEST.read_text(encoding="utf-8")) if LATEST.exists() else {}
    by = {x["id"]: x for x in st["ideas"]}
    L = [f"# Scalp lab report – {now()[:16]} UTC", "",
         f"Screens so far: {n_screens} (passed: {n_pass}). Rules live (alerts + paper) or judged: {len(ideas)}.",
         f"Live data until: {st.get('data_until', '-')}. Bear day now: {lv.get('bear_day', '-')} (alerts only on bear days).", "",
         "| | rule | since (UTC) | closed | days | avg | day t | worst closed | open now | note |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in ideas:
        s = by.get(r["id"], {})
        L.append(f"| {ICON.get(r['status'], '')} | {r['id']} | {r['start_ts'][:16]} | {s.get('trades', 0)} | {s.get('days', 0)} | "
                 f"{s.get('avg', '-')}% | {s.get('day_t', '-')} | {s.get('worst', [])[:1]} | {len(s.get('open', []))} | {r['status_why']} |")
    (HERE / "REPORT_latest.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    if not quiet:
        print("\n".join(L))


def cmd_list():
    with db() as c:
        for r in c.execute("SELECT id, status, start_ts, status_why FROM ideas ORDER BY entered"):
            print(dict(r))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["screen", "add", "scan", "report", "list"])
    ap.add_argument("file", nargs="?")
    ap.add_argument("--source", default="")
    ap.add_argument("--no-update", action="store_true")
    a = ap.parse_args()
    if a.cmd == "screen":
        cmd_screen(Path(a.file).resolve())
    elif a.cmd == "add":
        cmd_add(Path(a.file).resolve(), a.source)
    elif a.cmd == "scan":
        cmd_scan(update=not a.no_update)
    elif a.cmd == "report":
        cmd_report()
    else:
        cmd_list()


if __name__ == "__main__":
    main()
