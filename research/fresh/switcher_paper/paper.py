"""Switcher paper bot (2026-10-24) - no keys, no orders; public Binance futures candles only.
Rule: research/fresh/REGISTER_SWITCHER_2026-10-24.md (look-ahead-free version of switcher.py).

    .venv\\Scripts\\python.exe research\\fresh\\switcher_paper\\paper.py          # runs forever, wakes every hour
    .venv\\Scripts\\python.exe research\\fresh\\switcher_paper\\paper.py --once   # one pass, then exit

Every hour it fetches the closed 1h candles of the 220 coins, then rebuilds everything from the candles:
- reversal book R: rally_short + flush_long signals, exits as in bear_batch (stop / target / hold), trades opened
  only in weeks where R is picked; 300 USDT paper wallet, 50 USDT per trade, at most 6 open.
- momentum book M: each Monday, long the 10 strongest / short the 10 weakest by 30-day change, 15 USDT each, 7 days.
- pick for a week: higher 8-week average of what was KNOWN by its Monday (R trades closed, M weeks finished),
  cash if both <= 0. History before 2026-09-28 comes from the backtest weeks file.
Forward counting starts Monday 2026-10-26 00:00 UTC. Output: REPORT.md, status.json, trades.csv, log.txt.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
FRESH = HERE.parent
sys.path.insert(0, str(FRESH))
import bear_batch as bb  # noqa: E402

DATA = HERE / "data"
FORWARD = pd.Timestamp("2026-10-25 19:00", tz="UTC")   # 2026-10-25 Michael: "run the switcher today" (was 2026-10-26);
# candle index = open time, so entries use the close of the 19:00 candle (20:00 UTC, first close after the request). A week already running at
# FORWARD is joined at that price with the basket chosen on its Monday (the rule), not re-ranked.
LIVE_FROM = pd.Timestamp("2026-09-28", tz="UTC")   # weeks from here are rebuilt from fetched candles
WALLET, R_STAKE, R_SLOTS, M_N = 300.0, 50.0, 6, 10
URL = "https://fapi.binance.com/fapi/v1/klines?symbol={s}&interval=1h&limit={n}{st}"
IDEAS = ("rally_short", "flush_long")


def log(msg: str) -> None:
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}"
    print(line, flush=True)
    with (HERE / "log.txt").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def fetch(pair: str) -> pd.DataFrame | None:
    sym = pair.split("/")[0] + "USDT"
    f = DATA / f"{sym}.feather"
    old = pd.read_feather(f) if f.exists() else None
    st = f"&startTime={int(old['date'].iloc[-1].timestamp() * 1000)}" if old is not None and len(old) else ""
    try:
        raw = json.loads(urllib.request.urlopen(URL.format(s=sym, n=1500 if not st else 1000, st=st), timeout=20).read())
    except Exception as e:  # noqa: BLE001 - delisted / network; keep what we have
        if old is None:
            log(f"  {sym}: no data ({type(e).__name__})")
        return old.set_index("date") if old is not None else None
    now_ms = time.time() * 1000
    new = pd.DataFrame([r[:6] for r in raw if r[6] < now_ms], columns=["date", "open", "high", "low", "close", "volume"])
    new["date"] = pd.to_datetime(new["date"], unit="ms", utc=True)
    new[["open", "high", "low", "close", "volume"]] = new[["open", "high", "low", "close", "volume"]].astype(float)
    df = (pd.concat([old, new]) if old is not None else new).drop_duplicates("date", keep="last").sort_values("date")
    df = df.tail(2500).reset_index(drop=True)
    df.to_feather(f)
    return df.set_index("date")


def r_trades(df: pd.DataFrame) -> list[dict]:
    """All reversal-book signals on this coin since LIVE_FROM - 3 days, one trade per coin at a time; open ones kept open."""
    sigs, _ = bb.signals(df)
    o, c, h, l = df.index, df["close"].to_numpy(), df["high"].to_numpy(), df["low"].to_numpy()
    out = []
    for k in IDEAS:
        side, sl, tp, hold = bb.IDEAS[k]
        idx = np.flatnonzero(sigs[k].fillna(False).astype(bool).to_numpy() & (o >= LIVE_FROM - pd.Timedelta(days=3)))
        busy = -1
        for i in idx:
            if i <= busy:
                continue
            e, res, j = c[i], None, i
            for j in range(i + 1, min(i + hold, len(c) - 1) + 1):
                if side == "long":
                    res = -sl if l[j] <= e * (1 - sl) else tp if h[j] >= e * (1 + tp) else None
                else:
                    res = -sl if h[j] >= e * (1 + sl) else tp if l[j] <= e * (1 - tp) else None
                if res is not None:
                    break
            is_open = res is None and i + hold > len(c) - 1
            if res is None:
                res = (c[j] / e - 1) * (1 if side == "long" else -1)
            out.append({"idea": k, "side": side, "open": o[i], "close": None if is_open else o[j], "entry": e,
                        "last": c[j], "net": res - bb.COST, "is_open": is_open})
            busy = j if not is_open else len(c)
    return out


def monday(ts: pd.Series | pd.Timestamp):
    if isinstance(ts, pd.Timestamp):
        return (ts - pd.Timedelta(days=ts.dayofweek)).normalize()
    return (ts - pd.to_timedelta(ts.dt.dayofweek, unit="D")).dt.normalize()


def run_once() -> None:
    DATA.mkdir(exist_ok=True)
    frames, trades = {}, []
    for p in bb.PAIRS:
        df = fetch(p)
        time.sleep(0.25)
        if df is None or len(df) < 300:
            continue
        frames[p] = df
        trades += [{**t, "pair": p} for t in r_trades(df)]
    now = max(df.index[-1] for df in frames.values())
    C = pd.DataFrame({p: d["close"] for p, d in frames.items()})
    T = pd.DataFrame(trades)

    # ---- weekly results: backtest history, then rebuilt live weeks
    hist = pd.read_csv(FRESH / "bear_batch" / "switcher_weeks.csv", index_col=0, parse_dates=True)
    hist.index = hist.index.tz_localize("UTC") if hist.index.tz is None else hist.index
    hist = hist[hist.index < LIVE_FROM][["R", "M", "R_known"]]
    weeks = pd.date_range(LIVE_FROM, monday(now), freq="7D", tz="UTC")
    live = []
    for w in weeks:
        t0, t1 = w, w + pd.Timedelta(hours=168)
        row = {"R": np.nan, "M": np.nan, "R_known": np.nan}
        if len(T):
            done = T[(~T.is_open) & (monday(pd.to_datetime(T["close"], utc=True)) == w)]
            opened = T[monday(T["open"]) == w]
            row["R_known"] = done["net"].mean() if len(done) else 0.0
            row["R"] = opened["net"].mean() if len(opened) and not opened.is_open.any() else np.nan
        tm = t0 - pd.Timedelta(days=30)
        if t1 in C.index and tm in C.index and t0 in C.index:
            mom, fwd = (C.loc[t0] / C.loc[tm] - 1).dropna(), C.loc[t1] / C.loc[t0] - 1
            mom = mom[fwd.reindex(mom.index).notna()]
            row["M"] = (fwd[mom.nlargest(M_N).index].mean() - fwd[mom.nsmallest(M_N).index].mean()) / 2 - bb.COST
        live.append(pd.Series(row, name=w))
    W = pd.concat([hist, pd.DataFrame(live)])
    # pick for week w: 8 finished weeks before w, using what was known (R closed trades; M finished weeks)
    picks = {}
    for w in weeks:
        prev = W[W.index < w].tail(8)
        r, m = prev["R_known"].fillna(0).mean(), prev["M"].dropna().mean() if prev["M"].notna().any() else -1
        picks[w] = "cash" if max(r, m) <= 0 else ("R" if r >= m else "M")

    # ---- paper ledger from FORWARD on
    ledger, eq_real = [], 0.0
    if len(T):
        cand = T[T["open"] >= FORWARD].sort_values("open")
        open_until = []
        for _, t in cand.iterrows():
            if picks.get(monday(t["open"])) != "R":
                continue
            open_until = [x for x in open_until if x is None or x > t["open"]]
            if len(open_until) >= R_SLOTS:
                continue
            open_until.append(None if t.is_open else t["close"])
            ledger.append({"book": "R", "pair": t["pair"], "side": t["side"], "idea": t["idea"], "open": t["open"],
                           "close": t["close"], "entry": t["entry"], "now": t["last"], "usdt": R_STAKE * t["net"],
                           "is_open": bool(t.is_open)})
    for w in weeks:
        e0 = max(w, FORWARD)
        if w + pd.Timedelta(hours=168) <= FORWARD or picks.get(w) != "M" or w not in C.index or e0 not in C.index:
            continue
        tm, t1 = w - pd.Timedelta(days=30), w + pd.Timedelta(hours=168)
        mom = (C.loc[w] / C.loc[tm] - 1).dropna()
        end = t1 if t1 in C.index else C.index[-1]
        stake = WALLET / (2 * M_N)
        for side, names in (("long", mom.nlargest(M_N).index), ("short", mom.nsmallest(M_N).index)):
            for p in names:
                r = (C.loc[end, p] / C.loc[e0, p] - 1) * (1 if side == "long" else -1)
                ledger.append({"book": "M", "pair": p, "side": side, "idea": "basket", "open": e0, "close": end if end == t1 else None,
                               "entry": C.loc[e0, p], "now": C.loc[end, p], "usdt": stake * (r - bb.COST), "is_open": end != t1})
    L = pd.DataFrame(ledger)
    realized = float(L.loc[~L.is_open, "usdt"].sum()) if len(L) else 0.0
    unreal = float(L.loc[L.is_open, "usdt"].sum()) if len(L) else 0.0
    if len(L):
        L.to_csv(HERE / "trades.csv", index=False)

    this_week = monday(now)
    st = {"updated_utc": str(now + pd.Timedelta(hours=1)), "coins": len(frames), "forward_from": FORWARD.strftime("%Y-%m-%d %H:%M"),
          "pick_this_week": picks.get(this_week), "picks": {str(k.date()): v for k, v in picks.items()},
          "equity": round(WALLET + realized + unreal, 2), "realized": round(realized, 2), "open_pnl": round(unreal, 2),
          "trades_closed": int((~L.is_open).sum()) if len(L) else 0, "positions_open": int(L.is_open.sum()) if len(L) else 0,
          "checked_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "wallet": WALLET,
          "weeks": [{"week": str(w.date()), "pick": picks.get(w, "(backtest)"),
                     **{k: (None if pd.isna(W.loc[w, k]) else round(float(W.loc[w, k]) * 100, 2)) for k in ("R_known", "R", "M")}}
                    for w in W.index[-12:]],
          "positions": [] if not len(L) else [{k: (str(v) if isinstance(v, pd.Timestamp) else v) for k, v in r.items()}
                                              for r in L.sort_values("open", ascending=False).head(60)
                                              .assign(usdt=lambda x: x["usdt"].round(2)).to_dict("records")]}
    (HERE / "status.json").write_text(json.dumps(st, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")
    md = [f"# Switcher paper bot", "", f"Updated {st['updated_utc']} UTC. Paper only, 300 USDT, no orders. Forward count from **{FORWARD} (candle open)**.", "",
          f"- this week's pick: **{st['pick_this_week']}** (R = reversal book, M = momentum basket, cash)",
          f"- equity **{st['equity']}** (closed {st['realized']:+.2f}, open {st['open_pnl']:+.2f}); closed trades {st['trades_closed']}, open {st['positions_open']}",
          "", "| week | pick | R known (8-wk input) | R earned | M | ", "|---|---|---|---|---|"]
    for w in W.index[-10:]:
        f = lambda x: "-" if pd.isna(x) else f"{x * 100:+.2f}%"  # noqa: E731
        md.append(f"| {w.date()} | {picks.get(w, '(backtest)')} | {f(W.loc[w, 'R_known'])} | {f(W.loc[w, 'R'])} | {f(W.loc[w, 'M'])} |")
    if len(L) and L.is_open.any():
        md += ["", "Open positions:", ""] + [f"- {r.book} {r.side} {r.pair} since {r.open} entry {r.entry:.6g} now {r.now:.6g} -> {r.usdt:+.2f}"
                                            for r in L[L.is_open].itertuples()]
    (HERE / "REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    log(f"pass ok: {len(frames)} coins, last candle {now}, pick {st['pick_this_week']}, equity {st['equity']}")


def main() -> None:
    once = "--once" in sys.argv
    if not once:
        (HERE / "pid.txt").write_text(str(__import__("os").getpid()), encoding="utf-8")
    while True:
        try:
            run_once()
        except Exception as e:  # noqa: BLE001 - keep the loop alive, note the error
            log(f"ERROR {type(e).__name__}: {e}")
        if once:
            return
        due = time.time() // 3600 * 3600 + 3600 + 180   # next hour + 3 min (candle closed and published)
        while time.time() < due:                         # short naps: time.sleep does not count PC sleep on Windows
            time.sleep(60)


if __name__ == "__main__":
    main()
