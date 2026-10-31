"""Opportunity engine - forward test (the only test the rules cannot have been fitted to).

Every trigger the scanner sees is logged to forward.db with the tested trade (entry = open of the hour after the
trigger, target/stop from sigma24, time limit), whatever its badge. Each scan resolves open trades on real candles
with the casebook rule (stop counts first if both are hit in one hour; exit at the close of the last allowed hour;
0.2% round-trip costs; funding paid while open).

Effective badge (stated 2026-10-07, before any forward result existed):
  1. start from the dev badge in playbook.json (backtest on the coins the scanner really watches)
  2. (removed 2026-10-11 at Michael's request: the unseen-coin step no longer sets a badge; unseen_results.json is
     no longer read)
  3. forward, once >= 50 closed trades on >= 20 different days:
       day-weighted average <= 0              -> RED ("killed by forward test")
       day-weighted average > 0 and day t >= 2 -> YELLOW ("confirmed forward"); GREEN only after a human review
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
DB = HERE / "forward.db"
COST_RT = 0.002
MIN_N, MIN_DAYS = 50, 20
CLUSTER_MIN = 3          # same rule, same hour, >= 3 coins -> one market event, not separate opportunities
ICON = {"GREEN": "🟢", "YELLOW": "🟡", "ORANGE": "🟠", "RED": "🔴"}

SCHEMA = """CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY, symbol TEXT, coin TEXT, condition TEXT, direction TEXT, badge TEXT,
  trigger_time INTEGER, entry_time INTEGER, entry REAL, tgt_pct REAL, stp_pct REAL, target REAL, stop REAL,
  hours INTEGER, status TEXT, exit_time INTEGER, exit_price REAL, ret_pct REAL, funding_pct REAL,
  logged_at INTEGER, notified INTEGER DEFAULT 0, UNIQUE(symbol, condition, trigger_time))"""


def con() -> sqlite3.Connection:
    c = sqlite3.connect(DB, timeout=30)
    c.execute(SCHEMA)
    c.row_factory = sqlite3.Row
    return c


# ------------------------------------------------------------------ log
def log_alerts(alerts: list[dict]) -> list[dict]:
    """Insert new triggers; returns the rows that were new."""
    new, now = [], int(time.time())
    with con() as c:
        for a in alerts:
            trig = int(pd.Timestamp(a["trigger_bar"]).timestamp())
            known = a["hours_ago"] >= 1                     # the entry hour has closed -> its open is known
            entry = a["ref_price"] if known else None
            d = 1 if a["direction"] == "LONG" else -1
            row = (a["symbol"], a["coin"], a["condition"], a["direction"], a["badge"], trig, trig + 3600, entry,
                   a["target_pct"], a["stop_pct"],
                   entry * (1 + d * a["target_pct"] / 100) if entry else None,
                   entry * (1 - d * a["stop_pct"] / 100) if entry else None,
                   a["hours"], "open" if known else "pending", now)
            cur = c.execute("""INSERT OR IGNORE INTO alerts (symbol, coin, condition, direction, badge, trigger_time,
                entry_time, entry, tgt_pct, stp_pct, target, stop, hours, status, logged_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", row)
            if cur.rowcount:
                new.append({**a, "id": cur.lastrowid})
    return new


# ------------------------------------------------------------------ resolve
def resolve(get_candles, get_funding) -> int:
    """get_candles(symbol) -> DataFrame(date, open, high, low, close) of CLOSED 1h bars; get_funding(symbol) ->
    DataFrame(date, funding_rate). Returns the number of trades closed in this call."""
    closed = 0
    with con() as c:
        rows = c.execute("SELECT * FROM alerts WHERE status IN ('pending','open')").fetchall()
        by_sym: dict[str, list] = {}
        for r in rows:
            by_sym.setdefault(r["symbol"], []).append(r)
        for sym, rs in by_sym.items():
            try:
                df = get_candles(sym)
            except Exception:
                continue
            if df is None or df.empty:
                continue
            t = np.array([int(x.timestamp()) for x in df["date"]])
            o, h, l, cl = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
            fu = None
            for r in rs:
                d = 1 if r["direction"] == "LONG" else -1
                idx = np.flatnonzero(t == r["entry_time"])
                if not len(idx):
                    continue                                    # entry hour not closed yet (or data gap)
                e = int(idx[0])
                entry, target, stop = r["entry"], r["target"], r["stop"]
                if entry is None:                               # pending -> fill with the real open
                    entry = float(o[e])
                    target = entry * (1 + d * r["tgt_pct"] / 100)
                    stop = entry * (1 - d * r["stp_pct"] / 100)
                    c.execute("UPDATE alerts SET entry=?, target=?, stop=?, status='open' WHERE id=?",
                              (entry, target, stop, r["id"]))
                res = None
                for j in range(e, min(e + r["hours"], len(t))):
                    if (l[j] <= stop) if d == 1 else (h[j] >= stop):
                        res = ("stop", j, stop)
                        break
                    if (h[j] >= target) if d == 1 else (l[j] <= target):
                        res = ("target", j, target)
                        break
                if res is None and e + r["hours"] - 1 < len(t):
                    j = e + r["hours"] - 1
                    res = ("time", j, float(cl[j]))
                if res is None:
                    continue
                status, j, px = res
                if fu is None:
                    try:
                        fu = get_funding(sym)
                    except Exception:
                        fu = pd.DataFrame(columns=["date", "funding_rate"])
                ft = np.array([int(pd.Timestamp(x).floor("h").timestamp()) for x in fu["date"]]) if len(fu) else np.array([])
                paid = float(fu["funding_rate"].to_numpy()[(ft >= t[e]) & (ft <= t[j])].sum()) if len(ft) else 0.0
                ret = d * (px / entry - 1) - COST_RT - d * paid
                c.execute("UPDATE alerts SET status=?, exit_time=?, exit_price=?, ret_pct=?, funding_pct=? WHERE id=?",
                          (status, int(t[j]), px, round(ret * 100, 3), round(paid * 100, 4), r["id"]))
                closed += 1
    return closed


# ------------------------------------------------------------------ stats + badges
def forward_stats() -> dict:
    with con() as c:
        df = pd.read_sql("SELECT * FROM alerts", c)
    df = with_clusters(df)
    out = {}
    for cond, g in df.groupby("condition"):
        done = g[g["status"].isin(["target", "stop", "time"])]
        s = {"logged": int(len(g)), "open": int(g["status"].isin(["open", "pending"]).sum()), "closed": int(len(done))}
        if len(done):
            day = pd.to_datetime(done["entry_time"], unit="s").dt.floor("D")
            daily = done.groupby(day)["ret_pct"].mean()
            s.update({"days": int(len(daily)), "avg_pct": round(float(done["ret_pct"].mean()), 3),
                      "day_avg_pct": round(float(daily.mean()), 3),
                      "t_day": round(float(daily.mean() / daily.std(ddof=1) * np.sqrt(len(daily))), 2)
                      if len(daily) > 2 and daily.std() > 0 else None,
                      "win_pct": round(float((done["ret_pct"] > 0).mean() * 100), 1),
                      "target_pct": round(float((done["status"] == "target").mean() * 100), 1),
                      "stop_pct": round(float((done["status"] == "stop").mean() * 100), 1),
                      "time_pct": round(float((done["status"] == "time").mean() * 100), 1)})
        if len(done):
            # one market event = same rule, same trigger hour; average its coins first (the honest betting unit)
            ev = done.groupby("trigger_time")["ret_pct"].mean()
            solo, clus = done[done["cluster_n"] < CLUSTER_MIN], done[done["cluster_n"] >= CLUSTER_MIN]
            s.update({"events": int(len(ev)), "event_avg_pct": round(float(ev.mean()), 3),
                      "solo_n": int(len(solo)), "solo_avg_pct": round(float(solo["ret_pct"].mean()), 3) if len(solo) else None,
                      "cluster_n": int(len(clus)), "cluster_events": int(clus["trigger_time"].nunique()),
                      "cluster_avg_pct": round(float(clus["ret_pct"].mean()), 3) if len(clus) else None})
        out[cond] = s
    return out


def with_clusters(df: pd.DataFrame) -> pd.DataFrame:
    """cluster_n = how many coins triggered the same rule in the same hour (from the whole log)."""
    df = df.copy()
    df["cluster_n"] = df.groupby(["condition", "trigger_time"])["id"].transform("count") if len(df) else []
    return df


def effective_badges() -> dict:
    book = json.loads((HERE / "playbook.json").read_text(encoding="utf-8"))["conditions"]
    fwd = forward_stats()
    res = {}
    for name, r in book.items():
        badge, why = r["badge"], list(r["badge_why"])
        f = fwd.get(name, {})
        if f.get("closed", 0) >= MIN_N and f.get("days", 0) >= MIN_DAYS:
            if f["day_avg_pct"] <= 0:
                badge, why = "RED", [f"killed by forward test ({f['closed']} trades, day avg {f['day_avg_pct']:+.2f}%)"]
            elif (f.get("t_day") or 0) >= 2:
                badge, why = "YELLOW", [f"confirmed forward ({f['closed']} trades, day avg {f['day_avg_pct']:+.2f}%, t {f['t_day']})"]
        else:
            why.append(f"forward: {f.get('closed', 0)}/{MIN_N} closed on {f.get('days', 0)}/{MIN_DAYS} days")
        res[name] = {"badge": badge, "why": why, "dev_badge": r["badge"], "forward": f,
                     "direction": r["direction"], "hours": r["hours"], "description": r["description"],
                     "dev_test": r["test"]}
    (HERE / "badges.json").write_text(json.dumps({"updated": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
                                                  "rule": {"min_closed": MIN_N, "min_days": MIN_DAYS}, "conditions": res},
                                                 indent=1, default=str), encoding="utf-8")
    return res


# ------------------------------------------------------------------ notify
def notify(title: str, body: str) -> None:
    """Windows toast via Windows PowerShell 5.1 (WinRT). Silent no-op if it fails."""
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "''")
    ps = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null
$x = New-Object Windows.Data.Xml.Dom.XmlDocument
$x.LoadXml('<toast><visual><binding template="ToastGeneric"><text>{esc(title)}</text><text>{esc(body)}</text></binding></visual></toast>')
$id = '{{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}}\\WindowsPowerShell\\v1.0\\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($id).Show([Windows.UI.Notifications.ToastNotification]::new($x))
"""
    try:
        subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps], timeout=20,
                       capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception:
        pass


def notify_new(new_rows: list[dict], notify_all: bool = False) -> int:
    """One toast per market event (rule + trigger hour), not one per coin."""
    groups: dict[tuple, list[dict]] = {}
    for a in new_rows:
        if a["hours_ago"] > 2 or (a["badge"] == "RED" and not notify_all):
            continue
        groups.setdefault((a["condition"], a["trigger_bar"]), []).append(a)
    sent = 0
    with con() as c:
        for (cond, _), g in groups.items():
            g.sort(key=lambda a: -a.get("qv", 0))
            a = g[0]
            if len(g) == 1:
                notify(f"{ICON.get(a['badge'], '')} {a['coin']} {a['direction']} ({cond})",
                       f"Entry ~{a['ref_price']:.6g} · target {a['target']:.6g} · stop {a['stop']:.6g} · exit by {a['hours']}h. {a['badge_why'][0]}")
            else:
                notify(f"{ICON.get(a['badge'], '')} Market event: {cond} {a['direction']} on {len(g)} coins",
                       f"One event, not {len(g)} bets. Most liquid: {', '.join(x['coin'] for x in g[:3])}. {a['badge_why'][0]}")
            c.executemany("UPDATE alerts SET notified=1 WHERE id=?", [(x["id"],) for x in g])
            sent += 1
    return sent
