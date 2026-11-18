"""Bear lab: daily bear-short discovery -> paper on live data -> verdict on new data only. Rules: research/bear_lab/BEAR_LAB.md.

  .venv\\Scripts\\python.exe research\\bear_lab\\bear_lab.py screen research/bear_lab/ideas/X.py
  .venv\\Scripts\\python.exe research\\bear_lab\\bear_lab.py add research/bear_lab/ideas/X.py --source "agent 2026-11-02"
  .venv\\Scripts\\python.exe research\\bear_lab\\bear_lab.py evaluate      # forward trades since entry, verdicts, toast on PASS
  .venv\\Scripts\\python.exe research\\bear_lab\\bear_lab.py report
  .venv\\Scripts\\python.exe research\\bear_lab\\bear_lab.py list

An idea is one file in ideas/ (frozen by sha256 when it enters):
  SIDE = -1                      shorts only (RULES_BEAR)
  HOLD = 72                      max hours in the trade
  STOP = 0.08                    hard stop, fraction above entry (checked first inside a candle)
  TARGET = None                  optional take-profit fraction below entry
  GAP = 24                       min hours between two entries of the same coin
  REASON = "..."                 one line: who is forced to trade, why it repeats
  def signals(P) -> DataFrame[bool] (hours x coins), True on the closed 1h bar where the short is entered at its close.
The engine itself adds: bear day (BTC 20-day return <= 0 at the last daily close), 10M USDT 24h volume, one trade per
coin at a time, 0.20% round trip, real funding. P keys: see panels().

Data: history = data/market/main futures 1h + funding (2022-01 -> 2026-09) joined with the scanner's live_cache
(top-200 perps, closed 1h candles + funding, updated hourly) and data/market/oi (OI collector, 5m -> hourly).
"""
from __future__ import annotations

import argparse
import hashlib
import math
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IDEAS = HERE / "ideas"
DB = HERE / "bear_lab.db"
STATE = HERE / "state.json"
FUT = ROOT / "data" / "market" / "main" / "binance" / "futures"
LIVE = ROOT / "research" / "opportunity" / "live_cache"
OI = ROOT / "data" / "market" / "oi"
BTC_SPOT_1D = ROOT / "data" / "market" / "dev_1h" / "binance" / "BTC_USDT-1d.feather"
COINS = ["BTC", "ETH", "ZEC", "SOL", "XRP", "HYPE", "NEAR", "DOGE", "UNI", "BNB", "SUI", "ENA", "QNT", "ARB", "WLD",
         "PUMP", "LINK", "ADA", "TAO"]                      # trader COINS minus 1000PEPE (RULES_BEAR A1)
START = pd.Timestamp("2022-01-01", tz="UTC")
HIST_END = pd.Timestamp("2026-10-01", tz="UTC")              # screen window end (history files)
MID = pd.Timestamp("2024-05-01", tz="UTC")
COST = 0.002
# light history check before an idea may start paper (discovery is free; the forward verdict is strict)
SCREEN = {"min_trades": 100, "min_trades_half": 30, "min_avg_half": 0.0, "min_avg_2x": 0.0}
# forward verdict on new data only
VERDICT = {"min_trades": 40, "min_days": 12, "min_t": 2.5, "max_days": 180}
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
    CREATE TABLE IF NOT EXISTS evals (ts TEXT, id TEXT, stats TEXT);""")
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


def _candles(c: str) -> pd.DataFrame:
    parts = []
    f = FUT / f"{c}_USDT_USDT-1h-futures.feather"
    if f.exists():
        parts.append(_read(f))
    lf = LIVE / f"{c}USDT_1h.feather"
    if lf.exists():
        parts.append(_read(lf))
    d = pd.concat(parts).drop_duplicates("date", keep="last").set_index("date").sort_index()
    return d[["open", "high", "low", "close", "volume"]]


def _funding(c: str) -> pd.Series:
    parts = []
    f = FUT / f"{c}_USDT_USDT-1h-funding_rate.feather"
    if f.exists():
        parts.append(_read(f)[["date", "funding_rate"]])
    lf = LIVE / f"{c}USDT_funding.feather"
    if lf.exists():
        parts.append(_read(lf)[["date", "funding_rate"]])
    d = pd.concat(parts)
    d["date"] = d["date"].dt.round("h")
    return d.drop_duplicates("date", keep="last").set_index("date").sort_index().funding_rate


def _oi(c: str, col: str, H: pd.DatetimeIndex) -> pd.Series:
    p = OI / f"{c}.parquet"
    if not p.exists():
        return pd.Series(np.nan, index=H)
    s = pd.read_parquet(p, columns=[col])[col]
    return s.resample("h", label="left", closed="left").last().reindex(H)   # last 5m row <= bar open + 55 min


_PANELS = None


def panels() -> dict:
    """all inputs on one hourly grid 2022-01-01 -> last closed hour. Index = bar open time; values known at bar close."""
    global _PANELS
    if _PANELS is not None:
        return _PANELS
    raw = {c: _candles(c) for c in COINS}
    last = min(raw["BTC"].index.max(), pd.Timestamp.now(tz="UTC").floor("h") - pd.Timedelta(hours=1))
    H = pd.date_range(START, last, freq="h")
    P = {k: pd.DataFrame({c: raw[c][col].reindex(H) for c in COINS}) for k, col in
         (("O", "open"), ("H", "high"), ("L", "low"), ("C", "close"), ("V", "volume"))}
    P["QV"] = P["C"] * P["V"]
    T = H + pd.Timedelta(hours=1)
    P["FUND"] = pd.DataFrame({c: _funding(c).reindex(T).to_numpy() for c in COINS}, index=H)   # settled at bar close
    P["FUND_LAST"] = P["FUND"].ffill()
    for k, col in (("OI", "oi_usdt"), ("LS", "ls_accounts"), ("TOP", "top_ls_positions"), ("TAKER", "taker_ls_vol")):
        P[k] = pd.DataFrame({c: _oi(c, col, H) for c in COINS})
    P["ELIG"] = (P["QV"].rolling(24, min_periods=24).sum() >= 1e7) & P["C"].notna()
    # BTC daily closes: spot daily before 2022 (warm-up for the 200-day average), then the futures 23:00 bar
    spot = pd.read_feather(BTC_SPOT_1D).set_index("date").close
    spot.index = pd.to_datetime(spot.index, utc=True) + pd.Timedelta(days=1)
    btc = P["C"]["BTC"]
    fut = btc[btc.index.hour == 23].dropna()
    fut.index = fut.index.normalize() + pd.Timedelta(days=1)
    dc = pd.concat([spot[spot.index < fut.index[0]], fut]).sort_index()
    bear_day = dc / dc.shift(20) - 1 <= 0
    sma = dc.rolling(200).mean()
    deep_day = (dc < sma) & (sma < sma.shift(20))
    day = H.normalize()
    P["BEAR"] = pd.Series(day.map(bear_day).fillna(False).astype(bool), index=H).shift(-1, fill_value=False)
    P["DEEP"] = pd.Series(day.map(deep_day).fillna(False).astype(bool), index=H).shift(-1, fill_value=False)
    # last bar: the next bar's day flag is known at the close if the close is not 23:00; else from the new daily close
    if H[-1].hour == 23:
        nd = H[-1].normalize() + pd.Timedelta(days=1)
        P["BEAR"].iloc[-1] = bool(bear_day.get(nd, False))
        P["DEEP"].iloc[-1] = bool(deep_day.get(nd, False))
    else:
        P["BEAR"].iloc[-1] = bool(bear_day.get(H[-1].normalize(), False))
        P["DEEP"].iloc[-1] = bool(deep_day.get(H[-1].normalize(), False))
    P["INDEX"] = H
    P["COINS"] = COINS
    _PANELS = P
    return P


# helpers for idea files
def ema(df: pd.DataFrame, n: int) -> pd.DataFrame:
    return df.ewm(span=n, adjust=False, min_periods=n).mean()


def rank_prev(df: pd.DataFrame, n: int = 720) -> pd.DataFrame:
    """position of each value among the previous n values of the same column (0 = lowest, 1 = highest)."""
    return df.rolling(n + 1, min_periods=n + 1).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True)


# ---------------------------------------------------------------- engine
def trades(m, P: dict, a: pd.Timestamp, b: pd.Timestamp, include_open=False) -> pd.DataFrame:
    """short trades entered in [a, b). Engine rules are fixed here, not in the idea."""
    H = P["INDEX"]
    sig = m.signals(P)
    sig = sig.reindex(index=H, columns=COINS).fillna(False).astype(bool).to_numpy()
    base = sig & P["ELIG"].to_numpy() & P["BEAR"].to_numpy()[:, None]
    ok = np.asarray((H >= a) & (H < b))
    CL, HI, LO = P["C"].to_numpy(), P["H"].to_numpy(), P["L"].to_numpy()
    CF = P["FUND"].fillna(0).cumsum().to_numpy()
    hold, stop, target = int(m.HOLD), float(m.STOP), getattr(m, "TARGET", None)
    gap = int(getattr(m, "GAP", 0))
    n = len(H)
    rows = []
    for k, c in enumerate(COINS):
        busy, last_e = -1, -10 ** 9
        for i in np.flatnonzero(base[:, k] & ok):
            if i <= busy or i - last_e < gap or np.isnan(CL[i, k]):
                continue
            e = CL[i, k]
            sp = e * (1 + stop)
            tp = e * (1 - target) if target else None
            end = i + hold
            j, px, why = None, None, None
            for x in range(i + 1, min(end, n - 1) + 1):
                if np.isnan(CL[x, k]):
                    j, px, why = x - 1, CL[x - 1, k], "gap"
                    break
                if HI[x, k] >= sp:
                    j, px, why = x, sp, "stop"
                    break
                if tp is not None and LO[x, k] <= tp:
                    j, px, why = x, tp, "target"
                    break
                if x == end:
                    j, px, why = x, CL[x, k], "time"
            is_open = j is None
            if is_open:
                if not include_open:
                    busy = n
                    continue
                j, px, why = n - 1, CL[n - 1, k], "open"
            if j <= i:
                continue
            g = -(px / e - 1) + (CF[j, k] - CF[i, k])                  # a short receives positive funding
            rows.append((c, H[i], H[j], why, g - COST, g - 2 * COST))
            busy, last_e = (n if is_open else j), i
    return pd.DataFrame(rows, columns=["coin", "entry", "exit", "why", "net", "net2x"])



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
            "sum_pct": round(100 * tr.net.sum(), 1),
            "worst": [(r.coin, str(r.entry)[:16], round(100 * r.net, 2)) for r in tr.nsmallest(3, "net").itertuples()]}


# ---------------------------------------------------------------- commands
def code_sha() -> str:
    return sha(Path(__file__))


def check_idea_file(path: Path):
    m = load_idea(path)
    assert getattr(m, "SIDE", None) == -1, "SIDE must be -1 (shorts only)"
    for k in ("HOLD", "STOP", "REASON", "signals"):
        assert hasattr(m, k), f"missing {k}"
    assert 1 <= m.HOLD <= 24 * 30 and 0.005 <= m.STOP <= 0.25, "HOLD 1..720h, STOP 0.5%..25%"
    src = path.read_text(encoding="utf-8")
    for bad in ("shift(-", ".shift(periods=-", "bfill", "backfill", "center=True", "requests", "urllib", "ccxt", "open("):
        assert bad not in src, f"not allowed in an idea: {bad}"
    return m


def cmd_screen(path: Path) -> dict:
    m = check_idea_file(path)
    P = panels()
    tr = trades(m, P, START, HIST_END)
    s = summarize(tr)
    ok = (s.get("trades", 0) >= SCREEN["min_trades"] and s["trades_A"] >= SCREEN["min_trades_half"]
          and s["trades_B"] >= SCREEN["min_trades_half"] and (s["avg_A"] or -1) > SCREEN["min_avg_half"]
          and (s["avg_B"] or -1) > SCREEN["min_avg_half"] and s["avg_2x"] > SCREEN["min_avg_2x"])
    s["passed"] = bool(ok)
    with db() as c:
        c.execute("INSERT INTO screens VALUES (?,?,?,?,?)", (now(), str(path.as_posix()), sha(path), int(ok), json.dumps(s)))
        total = c.execute("SELECT COUNT(*) FROM screens").fetchone()[0]
    s["screens_so_far"] = total
    print(json.dumps(s, ensure_ascii=False))
    return s


def cmd_add(path: Path, source: str):
    h = sha(path)
    with db() as c:
        row = c.execute("SELECT result FROM screens WHERE sha=? AND passed=1 ORDER BY ts DESC", (h,)).fetchone()
        if row is None:
            sys.exit("not added: this exact file has no passed screen")
        today = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
        n_today = c.execute("SELECT COUNT(*) FROM ideas WHERE substr(entered,1,10)=?", (today,)).fetchone()[0]
        if n_today >= MAX_ADD_PER_DAY:
            sys.exit(f"not added: {MAX_ADD_PER_DAY} ideas already entered today")
        iid = path.stem
        if c.execute("SELECT 1 FROM ideas WHERE id=?", (iid,)).fetchone():
            sys.exit("not added: an idea with this name exists (a changed idea needs a new file name)")
        m = load_idea(path)
        start = pd.Timestamp.now(tz="UTC").floor("h")
        c.execute("INSERT INTO ideas VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (iid, str(path.as_posix()), h, code_sha(), source, m.REASON, now(), start.isoformat(), "PAPER", "",
                   row[0], now()))
    print(f"added {iid}: paper from {start} UTC")


def notify(title: str, body: str):
    try:
        sys.path.insert(0, str(ROOT / "research" / "opportunity"))
        import forward as FW
        FW.notify(title, body)
    except Exception:
        pass


def cmd_evaluate():
    P = panels()
    end = P["INDEX"][-1] + pd.Timedelta(hours=1)
    out = {"ts": now(), "data_until": str(end), "ideas": []}
    with db() as c:
        rows = c.execute("SELECT * FROM ideas WHERE status='PAPER'").fetchall()
        for r in rows:
            p = ROOT / r["file"]
            if not p.exists() or sha(p) != r["sha"] or r["code_sha"] != code_sha():
                c.execute("UPDATE ideas SET status='TAMPERED', status_why=?, updated=? WHERE id=?",
                          ("idea file or bear_lab.py changed after entry", now(), r["id"]))
                continue
            m = load_idea(p)
            start = pd.Timestamp(r["start_ts"])
            allt = trades(m, P, start, end, include_open=True)
            closed, opened = allt[allt.why != "open"], allt[allt.why == "open"]
            s = summarize(closed)
            s["open"] = [(x.coin, str(x.entry)[:16], round(100 * x.net, 2)) for x in opened.itertuples()]
            age = (end - start).days
            status, why = "PAPER", ""
            if s.get("trades", 0) >= VERDICT["min_trades"] and s["days"] >= VERDICT["min_days"]:
                if s["day_avg"] <= 0:
                    status, why = "KILLED", f"day average {s['day_avg']}% <= 0 after {s['trades']} trades"
                elif s["day_t"] >= VERDICT["min_t"] and s["avg_2x"] > 0:
                    status, why = "PASS", f"{s['trades']} trades on {s['days']} days, day avg {s['day_avg']}%, t {s['day_t']}"
            if status == "PAPER" and age >= VERDICT["max_days"]:
                status, why = "EXPIRED", f"no verdict after {age} days"
            c.execute("INSERT INTO evals VALUES (?,?,?)", (now(), r["id"], json.dumps(s)))
            if status != "PAPER":
                c.execute("UPDATE ideas SET status=?, status_why=?, updated=? WHERE id=?", (status, why, now(), r["id"]))
                if status == "PASS":
                    notify("Bear lab: idea PASSED on live data", f"{r['id']}: {why}")
                    with open(HERE / "PASSED.md", "a", encoding="utf-8") as fh:
                        fh.write(f"- {now()} {r['id']}: {why}. Worst closed: {s['worst']}. Open: {s['open']}\n")
            out["ideas"].append({"id": r["id"], "status": status, "why": why, "age_days": age, **s})
    STATE.write_text(json.dumps(out, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    print(f"evaluated {len(out['ideas'])} ideas, data until {end}")


def cmd_report():
    with db() as c:
        ideas = c.execute("SELECT id, status, status_why, entered, start_ts, reason FROM ideas ORDER BY entered").fetchall()
        n_screens = c.execute("SELECT COUNT(*) FROM screens").fetchone()[0]
        n_pass = c.execute("SELECT COUNT(*) FROM screens WHERE passed=1").fetchone()[0]
    st = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"ideas": []}
    by = {x["id"]: x for x in st["ideas"]}
    L = [f"# Bear lab report – {now()[:16]} UTC", "",
         f"Screens so far: {n_screens} (passed the light check: {n_pass}). Ideas on paper or judged: {len(ideas)}.",
         f"Live data until: {st.get('data_until', '-')}", "",
         "| | idea | since (UTC) | closed trades | days | avg | day t | worst closed | open now | note |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in ideas:
        s = by.get(r["id"], {})
        L.append(f"| {ICON.get(r['status'], '')} | {r['id']} | {r['start_ts'][:13]} | {s.get('trades', 0)} | {s.get('days', 0)} | "
                 f"{s.get('avg', '-')}% | {s.get('day_t', '-')} | {s.get('worst', [])[:1]} | {len(s.get('open', []))} | {r['status_why']} |")
    (HERE / "REPORT_latest.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


def cmd_list():
    with db() as c:
        for r in c.execute("SELECT id, status, start_ts, status_why FROM ideas ORDER BY entered"):
            print(dict(r))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["screen", "add", "evaluate", "report", "list"])
    ap.add_argument("file", nargs="?")
    ap.add_argument("--source", default="")
    a = ap.parse_args()
    if a.cmd == "screen":
        cmd_screen(Path(a.file).resolve())
    elif a.cmd == "add":
        cmd_add(Path(a.file).resolve(), a.source)
    elif a.cmd == "evaluate":
        cmd_evaluate()
    elif a.cmd == "report":
        cmd_report()
    else:
        cmd_list()


if __name__ == "__main__":
    main()
