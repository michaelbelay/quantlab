"""Crash-day forward log (Bear-Wild) - registered in C:\\quantlab\\FORWARD_2026-10-17_crashday.md (git 9bb774f).
Paper only: no orders, no bot.

Rule (frozen):
  Crash day D: BTC perp daily return <= -2 x sigma20 (std of the 20 daily returns before D) AND <= -4%.
  Cell at D's close = bullcalm_rule.market_condition at D+1 00:00 (Bear: 20d return <= 0; Wild: 20d vol > 365d median).
  Event = crash day in Bear-Wild; a crash day <= 2 days after the previous event's day is the same event (cluster).
  L / S: long / short BTC and ETH at the D+1 00:00 1h open, exit at the close of the 72nd 1h bar, stop 3 x sigma24
  (sigma24 = std of the last 720 1h log returns x sqrt(24)). Costs 0.10%/side + real funding. Event result = BTC/ETH avg.
  F: frozen incubator idea flush_f1 (incubator.rule_trades on the scanner's live_cache), signal bar on D or D+1.
  Verdict at 10 events or 2028-10-17 (descriptive look at 5): avg > 0, PF over events >= 1.3, >= 60% events positive
  (F also >= 30 trades).

Every run rebuilds BTC/ETH from public Binance data (missed runs lose nothing). Flush trades are frozen into events.json
once the window is closed (live_cache keeps ~200 days).

    .venv\\Scripts\\python.exe research\\fresh\\forward_crash\\crash_forward.py               # forward update
    .venv\\Scripts\\python.exe research\\fresh\\forward_crash\\crash_forward.py --replay 2021-01-01   # history, reference only
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT / "research"), str(ROOT / "research" / "incubator")]
import bullcalm_rule as BC  # noqa: E402

START = pd.Timestamp("2026-10-18", tz="UTC")           # first day that can be a crash day
COINS = ("BTC", "ETH")
CRASH_K, CRASH_MIN, CLUSTER_DAYS = 2.0, -0.04, 2
HOLD, STOP_MULT, SIDE_COST = 72, 3.0, 0.001
FLUSH_DAYS = 2                                         # signal bar on D or D+1
N_VERDICT, N_LOOK, DEADLINE = 10, 5, pd.Timestamp("2028-10-17", tz="UTC")
PASS = {"min_pf": 1.3, "min_pos": 0.60, "min_flush_trades": 30}


def get(url: str):
    for i in range(4):
        try:
            return json.loads(urllib.request.urlopen(url, timeout=30).read())
        except Exception:
            if i == 3:
                raise
            time.sleep(3 * (i + 1))


def ms(t: pd.Timestamp) -> int:
    return int(t.timestamp() * 1000)


def klines(coin: str, since: pd.Timestamp, interval: str = "1h") -> pd.DataFrame:
    """Closed futures candles from `since`, indexed by open time."""
    rows, t = [], ms(since)
    while True:
        r = get(f"https://fapi.binance.com/fapi/v1/klines?symbol={coin}USDT&interval={interval}&startTime={t}&limit=1500")
        rows += r
        if len(r) < 1500:
            break
        t = r[-1][0] + 1
    x = pd.DataFrame([row[:5] + [row[6]] for row in rows], columns=["t", "open", "high", "low", "close", "close_t"])
    x = x.astype({"open": float, "high": float, "low": float, "close": float})
    x = x[x.close_t < time.time() * 1000]
    x.index = pd.to_datetime(x.t, unit="ms", utc=True)
    x = x[["open", "high", "low", "close"]]
    return x.asfreq("1h").ffill() if interval == "1h" else x


def funding(coin: str, since: pd.Timestamp) -> pd.Series:
    rows, t = [], ms(since)
    while True:
        r = get(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={coin}USDT&startTime={t}&limit=1000")
        rows += r
        if len(r) < 1000:
            break
        t = r[-1]["fundingTime"] + 1
    if not rows:
        return pd.Series(dtype=float)
    s = pd.Series([float(r["fundingRate"]) for r in rows],
                  index=pd.to_datetime([r["fundingTime"] for r in rows], unit="ms", utc=True))
    return s.groupby(s.index.floor("1h")).sum()


# ------------------------------------------------------------------ 1. crash days and events
def crash_days(btc_d: pd.DataFrame, start: pd.Timestamp) -> list[dict]:
    c = btc_d["close"]
    r = c.pct_change()
    s20 = r.rolling(20).std().shift(1)
    daily = pd.DataFrame({"date": btc_d.index, "close": c.to_numpy()})
    out, last_event = [], None
    for day in c.index[(c.index >= start) & (r <= -CRASH_K * s20) & (r <= CRASH_MIN)]:
        cond = BC.market_condition(daily, (day + pd.Timedelta(days=1)).to_pydatetime())
        cell = None if not cond["ok"] else ("Bull" if cond["bull"] else "Bear") + "-" + ("Calm" if cond["calm"] else "Wild")
        row = {"day": str(day.date()), "btc_ret_pct": round(float(r[day]) * 100, 2),
               "sigma20_pct": round(float(s20[day]) * 100, 2), "cell": cell}
        if cell == "Bear-Wild":
            if last_event is not None and (day - last_event).days <= CLUSTER_DAYS:
                row["role"] = "cluster"                 # same event as the previous one
            else:
                row["role"] = "event"
            last_event = day
        else:
            row["role"] = "context"
        out.append(row)
    return out


# ------------------------------------------------------------------ 2. BTC/ETH legs
def sigma24(x: pd.DataFrame) -> np.ndarray:
    return (np.log(x["close"]).diff().rolling(720, min_periods=500).std() * np.sqrt(24)).to_numpy()


def leg(x: pd.DataFrame, sg: np.ndarray, fh: np.ndarray, t: pd.Timestamp, side: int) -> dict | None:
    if t not in x.index:
        return None
    o, h, l, c = (x[k].to_numpy() for k in ("open", "high", "low", "close"))
    i = int(x.index.searchsorted(t))
    if not np.isfinite(sg[i - 1]):
        return None
    e = o[i]
    stop = e * (1 - side * STOP_MULT * sg[i - 1])
    j_full = i + HOLD - 1
    j = min(j_full, len(x) - 1)
    for k in range(i, j + 1):
        if (l[k] <= stop) if side > 0 else (h[k] >= stop):
            px = stop if k == i else (min(o[k], stop) if side > 0 else max(o[k], stop))
            return {"status": "closed", "why": "stop", "entry": e, "stop": stop, "exit": float(px), "t_out": str(x.index[k]),
                    "ret_pct": round((side * (px / e - 1) - 2 * SIDE_COST - side * fh[i:k + 1].sum()) * 100, 3)}
    if j < j_full:
        return {"status": "open", "entry": e, "stop": stop, "last": float(c[-1]), "bars": int(len(x) - i),
                "upnl_pct": round((side * (c[-1] / e - 1) - 2 * SIDE_COST - side * fh[i:].sum()) * 100, 3)}
    return {"status": "closed", "why": "72h", "entry": e, "stop": stop, "exit": float(c[j]), "t_out": str(x.index[j]),
            "ret_pct": round((side * (c[j] / e - 1) - 2 * SIDE_COST - side * fh[i:j + 1].sum()) * 100, 3)}


def raw_returns(x: pd.DataFrame, t: pd.Timestamp) -> dict:
    i = int(x.index.searchsorted(t))
    e = x["open"].iloc[i]
    return {f"+{n}h": (round((x["close"].iloc[i + n - 1] / e - 1) * 100, 2) if i + n - 1 < len(x) else None)
            for n in (24, 72, 168)}


# ------------------------------------------------------------------ 3. flush trades (frozen incubator idea)
def live_ready(day: pd.Timestamp) -> bool:
    """live_cache must hold the last possible flush trade's exit: entry up to D+2 00:00, hold 24 h."""
    import incubator as I
    import downtrend as D
    b = pd.read_feather(I.LIVE / "BTCUSDT_1h.feather")
    return D.ns(b["date"]).max() >= day + pd.Timedelta(days=FLUSH_DAYS, hours=24)


def flush_trades(day: pd.Timestamp) -> list[dict]:
    """flush_f1 trades whose signal bar lies on D or D+1, computed by the incubator's own code on live_cache.
    Coins are loaded with full history (features need it), then sliced around the window to keep memory small;
    downtrend.load_coin's 'hist' column survives the slice, so the MIN_HIST check is unchanged."""
    import downtrend as D
    import incubator as I
    m = I.load_idea(ROOT / "research" / "incubator" / "ideas" / "flush_f1.py")
    a, b = day + pd.Timedelta(hours=1), day + pd.Timedelta(days=FLUSH_DAYS, hours=1)   # entry = signal bar + 1 h
    lo, hi = day - pd.Timedelta(days=3), day + pd.Timedelta(days=FLUSH_DAYS + 3)
    orig = D.load_coin

    def sliced(p, fp):
        d = orig(p, fp)
        return None if d is None else d.loc[lo:hi]
    D.load_coin = sliced
    try:
        U = D.Universe(I.live_files())
    finally:
        D.load_coin = orig
    tr = I.rule_trades(U, m, I.live_types(), a.isoformat(), b.isoformat())
    return [{"coin": r.coin, "entry_t": str(r.date), "pnl_pct": round(float(r.pnl), 3), "stopped": bool(r.stopped)}
            for r in tr.itertuples()]


# ------------------------------------------------------------------ 4. verdict
def judge(vals: list[float], extra_ok: bool = True) -> dict:
    v = np.array([x for x in vals if x is not None], float)
    if not len(v):
        return {"events": 0}
    loss = -v[v < 0].sum()
    pf = float(v[v > 0].sum() / loss) if loss > 0 else None
    ok = v.mean() > 0 and (pf is None or pf >= PASS["min_pf"]) and (v > 0).mean() >= PASS["min_pos"] and extra_ok
    return {"events": int(len(v)), "avg_pct": round(float(v.mean()), 3), "pf": None if pf is None else round(pf, 2),
            "pos_share": round(float((v > 0).mean()), 2), "would_pass": bool(ok)}


def build(start: pd.Timestamp, frozen: dict, with_flush: bool) -> dict:
    btc_d = klines("BTC", start - pd.Timedelta(days=420), "1d")
    days = crash_days(btc_d, start)
    latest = latest_close(btc_d)
    hist0 = start - pd.Timedelta(days=45)
    xs = {c: klines(c, hist0) for c in COINS}
    fus = {c: funding(c, start - pd.Timedelta(days=1)).reindex(xs[c].index).fillna(0.0).to_numpy() for c in COINS}
    sgs = {c: sigma24(xs[c]) for c in COINS}
    events = []
    for row in days:
        day = pd.Timestamp(row["day"], tz="UTC")
        t = day + pd.Timedelta(days=1)
        if row["role"] != "event":
            events.append(row)
            continue
        legs = {f"{s}_{c}": leg(xs[c], sgs[c], fus[c], t, side) for c in COINS for s, side in (("L", 1), ("S", -1))}
        row["legs"] = legs
        row["raw"] = {c: raw_returns(xs[c], t) for c in COINS if t in xs[c].index}
        for s in ("L", "S"):
            lr = [legs[f"{s}_{c}"] for c in COINS]
            row[s] = round(float(np.mean([x["ret_pct"] for x in lr])), 3) \
                if all(x and x["status"] == "closed" for x in lr) else None
        if with_flush:
            key = row["day"]
            if key in frozen:
                row["flush"] = frozen[key]
            elif live_ready(day):
                ft = flush_trades(day)
                row["flush"] = frozen[key] = {"trades": ft, "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            else:
                row["flush"] = None                    # window not closed yet
            f = row["flush"]
            row["F"] = round(float(np.mean([x["pnl_pct"] for x in f["trades"]])), 3) if f and f["trades"] else None
        events.append(row)
    return {"days": events, "frozen": frozen, "latest": latest}


def latest_close(btc_d: pd.DataFrame) -> dict:
    """Display only (UI): the last closed BTC day measured against the crash line, and the cell at its close."""
    c = btc_d["close"]
    r = c.pct_change()
    s20 = r.rolling(20).std().shift(1)
    day = c.index[-1]
    line = min(-CRASH_K * float(s20.iloc[-1]), CRASH_MIN)
    cond = BC.market_condition(pd.DataFrame({"date": btc_d.index, "close": c.to_numpy()}),
                               (day + pd.Timedelta(days=1)).to_pydatetime())
    cell = None if not cond["ok"] else ("Bull" if cond["bull"] else "Bear") + "-" + ("Calm" if cond["calm"] else "Wild")
    return {"day": str(day.date()), "btc_ret_pct": round(float(r.iloc[-1]) * 100, 2),
            "crash_line_pct": round(line * 100, 2), "crash": bool(r.iloc[-1] <= line), "cell": cell}


def summary(rows: list[dict]) -> dict:
    ev = [r for r in rows if r.get("role") == "event"]
    done = [r for r in ev if r.get("L") is not None]
    n_flush = sum(len(r["flush"]["trades"]) for r in ev if r.get("flush"))
    out = {"events": len(ev), "events_closed": len(done),
           "L": judge([r["L"] for r in done]), "S": judge([r["S"] for r in done]),
           "F": judge([r.get("F") for r in done], n_flush >= PASS["min_flush_trades"]), "flush_trades": n_flush}
    now = pd.Timestamp.now(tz="UTC")
    if len(done) >= N_VERDICT or now >= DEADLINE:
        out["stage"] = "VERDICT" if len(done) >= N_LOOK else "TOO RARE - Michael decides"
    elif len(done) >= N_LOOK:
        out["stage"] = f"descriptive look ({len(done)}/{N_VERDICT} events, no verdict yet)"
    else:
        out["stage"] = f"running ({len(done)}/{N_VERDICT} events)"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", help="history from this day, reference only (writes replay.json, no flush)")
    a = ap.parse_args()
    if a.replay:
        res = build(pd.Timestamp(a.replay, tz="UTC"), {}, with_flush=False)
        out = {"note": "historical replay, reference only - NOT part of the forward verdict", "from": a.replay,
               "summary": summary(res["days"]), "days": res["days"]}
        (HERE / "replay.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
        print(json.dumps(out["summary"], indent=1))
        return
    ev_file = HERE / "events.json"
    frozen = json.loads(ev_file.read_text(encoding="utf-8")) if ev_file.exists() else {}
    res = build(START, frozen, with_flush=True)
    ev_file.write_text(json.dumps(res["frozen"], indent=1, default=str), encoding="utf-8")
    s = summary(res["days"])
    state = {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "forward_start": str(START.date()),
             "register": r"C:\quantlab\FORWARD_2026-10-17_crashday.md",
             "rule": "BTC day <= -2 sigma20 and <= -4%, cell Bear-Wild at the close -> L/S BTC+ETH 72h stop 3 sigma24; F = flush_f1 on D/D+1",
             "summary": s, "latest_close": res["latest"], "days": res["days"]}
    (HERE / "state.json").write_text(json.dumps(state, indent=1, default=str), encoding="utf-8")
    with open(HERE / "run.log", "a", encoding="utf-8") as f:
        f.write(f"{state['updated']} crash days {len(res['days'])} events {s['events']} closed {s['events_closed']} | {s['stage']}\n")
    print(json.dumps({k: v for k, v in state.items() if k != "days"}, indent=1, default=str))


if __name__ == "__main__":
    main()
