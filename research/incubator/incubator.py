"""Strategy incubator: discovery -> incubation on new data -> verdict. Rules: research/incubator/INCUBATOR.md.

  python research\\incubator\\incubator.py screen ideas\\X.py        # light check on development data (discovery)
  python research\\incubator\\incubator.py add ideas\\X.py --source "..." [--manual "reason"]
  python research\\incubator\\incubator.py evaluate                  # daily: forward trades since entry, verdicts
  python research\\incubator\\incubator.py report                    # weekly plain-language report
  python research\\incubator\\incubator.py list

An idea is a Python file in ideas/ (frozen by sha256 when it enters). Two kinds:
  KIND = "rule":   SIDE (+1/-1), HOLD (bars), STOP_K (stop = k x sigma), MARKET (None | "UP" | "DN" | a type name),
                   def signals(g) -> boolean Series on the signal bar (g = all coins concatenated, columns of
                   downtrend.load_coin plus 'coin' and 'date'). Entry = next bar open.
  KIND = "engine": BOOK = {market_type_or_"ALL": [pipeline candidate ids]}; trades of a candidate count only on
                   entry days of its type; weight 1 / number of candidates in that type.
Forward data = the hourly scanner's live_cache (top-200 Binance USDT perps, closed 1h candles + funding).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IDEAS = HERE / "ideas"
DB = HERE / "incubator.db"
STATE = HERE / "state.json"
LIVE = ROOT / "research" / "opportunity" / "live_cache"
BTC_1D = ROOT / "data" / "market" / "dev_1h" / "binance" / "futures" / "BTC_USDT_USDT-1d-futures.feather"
sys.path[:0] = [str(ROOT / "research"), str(ROOT / "research" / "engine"), str(ROOT / "research" / "pipeline")]
import downtrend as D  # noqa: E402

FROZEN_CODE = ["research/incubator/incubator.py", "research/downtrend.py"]   # hashed in code_hashes.txt
SCREEN = {"min_trades": 200, "min_pf": 1.10, "min_pf_2x": 1.00, "min_t": 2.0, "min_years_pos": 4, "years": 6,
          "window": ("2021-01-01", "2026-09-19")}
DEFAULT_RULE = {"min_trades": 50, "min_days": 20, "max_days": 365}
ICON = {"INCUBATING": "🧪", "PROMOTED": "🟡", "KILLED": "🔴", "EXPIRED": "⚪", "TAMPERED": "⛔"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def db() -> sqlite3.Connection:
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE IF NOT EXISTS ideas (id TEXT PRIMARY KEY, name TEXT, file TEXT, sha TEXT, kind TEXT, source TEXT,
      reason TEXT, entered TEXT, start_ts TEXT, rule TEXT, status TEXT, status_why TEXT, screen TEXT, updated TEXT);
    CREATE TABLE IF NOT EXISTS screens (ts TEXT, file TEXT, sha TEXT, passed INTEGER, result TEXT);
    CREATE TABLE IF NOT EXISTS evals (ts TEXT, id TEXT, stats TEXT);""")
    return c


def load_idea(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ------------------------------------------------------------------ market types
def types_from_daily(c: pd.Series) -> pd.Series:
    """Same definition as regime_switch.market_types, on any daily close series (index = UTC day)."""
    sma = c.rolling(50).mean()
    vol = np.log(c).diff().rolling(20).std()
    med = vol.rolling(365, min_periods=60).median()
    st = pd.Series(np.where(c > sma, "UP", "DN"), index=c.index) + pd.Series(np.where(vol > med, "_HIVOL", "_LOVOL"), index=c.index)
    st[sma.isna() | med.isna() | vol.isna()] = None
    return st.shift(1)


def live_types() -> pd.Series:
    """BTC daily closes: history file, extended with the scanner's live 1h candles (close of the 23:00 bar)."""
    h = pd.read_feather(BTC_1D)
    h["date"] = D.ns(h["date"])
    c = h.set_index("date").close
    live = pd.read_feather(LIVE / "BTCUSDT_1h.feather")
    live["date"] = D.ns(live["date"])
    l = live.set_index("date").close
    l = l[l.index.hour == 23]
    l.index = l.index.floor("D")
    c = pd.concat([c[c.index < l.index.min()], l]).sort_index()
    c = c[~c.index.duplicated(keep="last")]
    # the 1d file's row for day D is the candle opening at D (close = end of D); the 23:00 bar closes at the same time.
    # One empty day appended so the type of the day after the last close (= today) exists after the shift.
    c = pd.concat([c, pd.Series([np.nan], index=[c.index.max() + pd.Timedelta(days=1)])])
    return types_from_daily(c)


def live_files():
    out = []
    for p in sorted(LIVE.glob("*_1h.feather")):
        sid = p.name[:-len("_1h.feather")]
        out.append((sid[:-4] if sid.endswith("USDT") else sid, p, LIVE / f"{sid}_funding.feather"))
    return out


# ------------------------------------------------------------------ trades of one idea
def in_market(day_type: pd.Series, market) -> np.ndarray:
    if market in (None, "ALL"):
        return np.ones(len(day_type), bool)
    return day_type.fillna("").str.startswith(market).to_numpy() if market in ("UP", "DN") \
        else (day_type == market).to_numpy()


def rule_trades(U, m, types, a, b) -> pd.DataFrame:
    g = U.g
    mask = m.signals(g).fillna(False).to_numpy(bool)
    ent_date = U.date.shift(-1)
    dt = ent_date.dt.floor("D").map(types)
    valid = U.ok & np.r_[U.ok[1:], False] & in_market(dt, getattr(m, "MARKET", None))
    sig = np.flatnonzero(mask & valid)
    ent = sig + 1
    d = U.date.iloc[ent]
    w = ((d >= pd.Timestamp(a, tz="UTC")) & (d < pd.Timestamp(b, tz="UTC"))).to_numpy()
    sig, ent = sig[w], ent[w]
    tr = D.simulate(U, ent, m.SIDE, np.full(len(ent), m.HOLD), m.STOP_K, g.sigma.to_numpy(float)[sig])
    tr = D.no_stack(U, tr)
    tr["date"] = pd.to_datetime(U.date.iloc[tr.ent.to_numpy()].to_numpy(), utc=True)
    tr["day"] = tr["date"].dt.floor("D")
    tr["coin"] = g.coin.iloc[tr.ent.to_numpy()].to_numpy()
    tr["w"] = 1.0
    return tr


def engine_trades(files, book: dict, types, a, b) -> pd.DataFrame:
    import backtest as BT
    R = load_idea(ROOT / "research" / "pipeline" / "run.py")    # pipeline run.py (engine/ has its own run.py)
    con = sqlite3.connect(f"file:{ROOT / 'research' / 'pipeline' / 'pipeline.db'}?mode=ro", uri=True)
    specs = {}
    for ids in book.values():
        for i in ids:
            s, c = con.execute("select spec, cfg from candidates where id=?", (i,)).fetchone()
            specs[i] = (json.loads(s), R.to_cfg(json.loads(c)))
    rows = []
    for coin, p, fp in files:
        try:
            f = R.load(p, fp)
        except Exception:
            continue
        if f is None:
            continue
        dates = pd.to_datetime(f.date, utc=True)
        for i, (spec, cfg) in specs.items():
            try:
                tr = BT.simulate_pair(f, spec, cfg, coin)
            except Exception:
                continue
            for t in tr:
                if t.reason == "eod":
                    continue                                  # still open at the end of the data
                rows.append((i, coin, t.pnl / t.notional * 100 if t.notional else 0.0, dates[t.entry_i]))
    tr = pd.DataFrame(rows, columns=["cid", "coin", "pnl", "date"])
    tr = tr[(tr.date >= pd.Timestamp(a, tz="UTC")) & (tr.date < pd.Timestamp(b, tz="UTC"))].copy()
    tr["day"] = tr.date.dt.floor("D")
    dt = tr.day.map(types)
    parts = []
    for ty, ids in book.items():
        ok = in_market(dt, ty)
        for i in ids:
            parts.append(tr[ok & (tr.cid == i).to_numpy()].assign(w=1.0 / len(ids)))
    out = pd.concat(parts) if parts else tr.assign(w=1.0)
    out["stopped"] = False
    return out


def idea_trades(m, files_or_U, types, a, b):
    if m.KIND == "engine":
        return engine_trades(files_or_U["files"], m.BOOK, types, a, b)
    return rule_trades(files_or_U["U"], m, types, a, b)


def summarize(tr: pd.DataFrame) -> dict:
    if tr is None or not len(tr):
        return {"trades": 0, "days": 0}
    p = (tr.pnl * tr.w).to_numpy()
    p2 = ((tr.pnl - D.EXTRA) * tr.w).to_numpy()
    daily = (tr.pnl * tr.w).groupby(tr.day).sum() / tr.w.groupby(tr.day).sum()
    t = float(daily.mean() / daily.std(ddof=1) * np.sqrt(len(daily))) if len(daily) > 2 and daily.std(ddof=1) > 0 else None
    years = (tr.pnl * tr.w).groupby(tr.date.dt.year).agg(["sum", "size"])
    return {"trades": int(len(tr)), "days": int(len(daily)), "pf": D.pf(p), "pf_2x": D.pf(p2),
            "avg_pct": float(np.average(tr.pnl, weights=tr.w)), "day_avg_pct": float(daily.mean()), "day_t": t,
            "win_pct": float((tr.pnl > 0).mean() * 100),
            "years": {int(y): {"net": float(r["sum"]), "trades": int(r["size"])} for y, r in years.iterrows()},
            "first": str(tr.date.min()), "last": str(tr.date.max())}


# ------------------------------------------------------------------ commands
def cmd_screen(path: Path) -> dict:
    """Discovery check on DEVELOPMENT coins (2021..2026-09). Light gates; every screen is logged as a trial."""
    m = load_idea(path)
    from regime_switch import market_types
    types = market_types()
    ctx = {"files": D.dev_files()} if m.KIND == "engine" else {"U": D.Universe(D.dev_files())}
    tr = idea_trades(m, ctx, types, *SCREEN["window"])
    s = summarize(tr)
    yrs = [v for v in s.get("years", {}).values() if v["trades"] >= 20]
    chk = {"trades": s["trades"] >= SCREEN["min_trades"], "pf": (s.get("pf") or 0) >= SCREEN["min_pf"],
           "pf_2x": (s.get("pf_2x") or 0) >= SCREEN["min_pf_2x"], "day_t": (s.get("day_t") or 0) >= SCREEN["min_t"],
           "years_positive": sum(v["net"] > 0 for v in yrs) >= SCREEN["min_years_pos"]}
    res = {"file": str(path.relative_to(ROOT)), "sha": sha(path), "name": getattr(m, "NAME", path.stem),
           "stats": s, "checks": chk, "passed": all(chk.values())}
    with db() as c:
        n_before = c.execute("SELECT COUNT(*) FROM screens").fetchone()[0]
        c.execute("INSERT INTO screens VALUES (?,?,?,?,?)", (now(), res["file"], res["sha"], int(res["passed"]),
                                                          json.dumps(res, default=str)))
    res["trial_number"] = n_before + 1
    print(json.dumps(res, indent=1, default=str))
    return res


def cmd_add(path: Path, source: str, manual: str | None, rule: dict | None = None):
    m = load_idea(path)
    h = sha(path)
    with db() as c:
        scr = c.execute("SELECT result FROM screens WHERE sha=? AND passed=1 ORDER BY ts DESC", (h,)).fetchone()
        if scr is None and not manual:
            sys.exit("refused: this exact file has no passing screen (run screen first, or --manual with a reason)")
        iid = path.stem
        if c.execute("SELECT 1 FROM ideas WHERE id=?", (iid,)).fetchone():
            sys.exit(f"refused: {iid} is already registered (a changed idea needs a new file name)")
        rule = rule or {**DEFAULT_RULE, **getattr(m, "RULE", {})}
        start = pd.Timestamp.now(tz="UTC").floor("h").isoformat()
        c.execute("INSERT INTO ideas VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (iid, getattr(m, "NAME", iid), str(path.relative_to(ROOT)), h, m.KIND, source, manual or "screen passed",
                   now(), start, json.dumps(rule), "INCUBATING", "", scr[0] if scr else None, now()))
    print(f"added {iid}: forward start {start}, rule {rule}")


def check_code() -> list[str]:
    f = HERE / "code_hashes.txt"
    if not f.exists():
        return []
    bad = []
    for line in f.read_text(encoding="utf-8").splitlines():
        h, p = line.split(maxsplit=1)
        if sha(ROOT / p) != h:
            bad.append(p)
    return bad


def cmd_evaluate():
    bad_code = check_code()
    types = live_types()
    files = live_files()
    U = None
    end = (pd.Timestamp.now(tz="UTC") + pd.Timedelta(hours=1)).isoformat()
    changes, out = [], {}
    with db() as c:
        ideas = c.execute("SELECT * FROM ideas ORDER BY entered").fetchall()
    for r in ideas:
        path = ROOT / r["file"]
        st, why = r["status"], r["status_why"]
        if st in ("INCUBATING",) and (not path.exists() or sha(path) != r["sha"] or bad_code):
            st, why = "TAMPERED", "idea file or incubator code changed after entry: " + (", ".join(bad_code) or r["file"])
        s = {}
        if st == "INCUBATING":
            m = load_idea(path)
            if m.KIND == "rule" and U is None:
                U = D.Universe(files)
            tr = idea_trades(m, {"files": files, "U": U}, types, r["start_ts"], end)
            s = summarize(tr)
            rule = json.loads(r["rule"])
            age = (pd.Timestamp.now(tz="UTC") - pd.Timestamp(r["start_ts"])).days
            if s["trades"] >= rule["min_trades"] and s["days"] >= rule["min_days"]:
                if s["day_avg_pct"] <= 0:
                    st, why = "KILLED", f"forward {s['trades']} trades / {s['days']} days, day avg {s['day_avg_pct']:+.2f}%"
                elif (s["day_t"] or 0) >= 2 and (s["pf_2x"] or 0) >= 1.0:
                    st, why = "PROMOTED", f"forward {s['trades']} trades / {s['days']} days, day avg {s['day_avg_pct']:+.2f}%, t {s['day_t']:.2f}"
            if st == "INCUBATING" and age >= rule["max_days"]:
                st, why = "EXPIRED", f"{age} days without reaching a verdict ({s['trades']} trades / {s['days']} days)"
            if len(tr):
                tr.to_parquet(HERE / "trades" / f"{r['id']}.parquet") if (HERE / "trades").exists() else None
        else:
            last = None
            with db() as c:
                last = c.execute("SELECT stats FROM evals WHERE id=? ORDER BY ts DESC", (r["id"],)).fetchone()
            s = json.loads(last[0]) if last else {}
        with db() as c:
            if st != r["status"]:
                c.execute("UPDATE ideas SET status=?, status_why=?, updated=? WHERE id=?", (st, why, now(), r["id"]))
                changes.append((r["id"], r["status"], st, why))
            if r["status"] == "INCUBATING":
                c.execute("INSERT INTO evals VALUES (?,?,?)", (now(), r["id"], json.dumps(s, default=str)))
        out[r["id"]] = {"name": r["name"], "kind": r["kind"], "source": r["source"], "reason": r["reason"],
                        "entered": r["entered"], "start": r["start_ts"], "rule": json.loads(r["rule"]),
                        "status": st, "why": why, "forward": s}
    with db() as c:
        n_screens = c.execute("SELECT COUNT(*), SUM(passed) FROM screens").fetchone()
    state = {"updated": now(), "data_until": str(max(pd.read_feather(p).date.max() for _, p, _ in files[:3])),
             "market_type_today": types.iloc[-1], "ideas": out, "screens": {"total": n_screens[0], "passed": n_screens[1] or 0},
             "code_ok": not bad_code, "changes": changes}
    STATE.write_text(json.dumps(state, indent=1, default=str), encoding="utf-8")
    for iid, old, new, why in changes:
        notify(f"Incubator: {iid} {ICON.get(new, '')} {new}", why)
    print(f"evaluated {len(out)} ideas; changes: {changes or 'none'}; market type today {types.iloc[-1]}")


def cmd_report():
    s = json.loads(STATE.read_text(encoding="utf-8"))
    badges = ROOT / "research" / "opportunity" / "badges.json"
    lines = [f"# Incubator report {now()[:10]}", "",
             f"Data until {s['data_until']}. BTC market type today: **{s['market_type_today']}**. "
             f"Discovery trials so far: {s['screens']['total']} screened, {s['screens']['passed']} passed the light check.", ""]
    if not s.get("code_ok", True):
        lines += ["**⛔ Incubator code changed after it was frozen — verdicts are on hold until reviewed.**", ""]
    lines += ["| Idea | Status | Forward trades / days | Day avg | t | Needed | Since |", "|---|---|---|---|---|---|---|"]
    for iid, v in s["ideas"].items():
        f, r = v["forward"], v["rule"]
        lines.append(f"| {v['name']} | {ICON.get(v['status'], '')} {v['status']} | {f.get('trades', 0)} / {f.get('days', 0)} | "
                     f"{f['day_avg_pct']:+.2f}% |" if f.get("trades") else
                     f"| {v['name']} | {ICON.get(v['status'], '')} {v['status']} | 0 / 0 | – |")
        lines[-1] += (f" {f['day_t']:.2f} |" if f.get("day_t") is not None else " – |") + \
            f" {r['min_trades']} trades on {r['min_days']} days | {v['start'][:10]} |"
    if badges.exists():
        b = json.loads(badges.read_text(encoding="utf-8"))["conditions"]
        lines += ["", "Scanner rules (hourly forward log, judged by forward.py): " +
                  ", ".join(f"{k} {v['forward'].get('closed', 0)}/50" for k, v in b.items())]
    ch = [f"- {i}: {o} → {n} ({w})" for i, o, n, w in s.get("changes", [])]
    lines += ["", "Changes at the last evaluation:", *(ch or ["- none"])]
    txt = "\n".join(lines) + "\n"
    (HERE / "REPORT_latest.md").write_text(txt, encoding="utf-8")
    print(txt)


def cmd_list():
    with db() as c:
        for r in c.execute("SELECT id, status, kind, start_ts, source FROM ideas ORDER BY entered"):
            print(dict(r))


def notify(title, body):
    try:
        sys.path.insert(0, str(ROOT / "research" / "opportunity"))
        import forward as FW
        FW.notify(title, body)
    except Exception:
        pass


def now() -> str:
    return pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["screen", "add", "evaluate", "report", "list"])
    ap.add_argument("file", nargs="?")
    ap.add_argument("--source", default="")
    ap.add_argument("--manual")
    a = ap.parse_args()
    (HERE / "trades").mkdir(exist_ok=True)
    if a.cmd == "screen":
        cmd_screen(Path(a.file).resolve())
    elif a.cmd == "add":
        cmd_add(Path(a.file).resolve(), a.source, a.manual)
    elif a.cmd == "evaluate":
        cmd_evaluate()
    elif a.cmd == "report":
        cmd_report()
    else:
        cmd_list()


if __name__ == "__main__":
    main()
