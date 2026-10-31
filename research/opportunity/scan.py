"""Opportunity engine - live scan of the top Binance USDT perpetuals.

Uses Binance PUBLIC market data (no API key). Candles and funding are cached
in live_cache/ so only the first run is slow. Conditions are computed with the
same code as the casebook (common.py); each fresh trigger is matched to its
playbook rule and printed as an alert. You decide - nothing is traded.

Run:  .venv\\Scripts\\python.exe research\\opportunity\\scan.py [--top 200] [--fresh 3] [--all]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import ccxt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from common import CONDITIONS, COST_RT, compute_conditions, regular_grid, triggers
import forward as FW  # noqa: E402

HERE = Path(__file__).parent
CACHE = HERE / "live_cache"
HOURS_NEEDED = 4600            # SQUEEZE needs ~180 days of 1h candles
ACCOUNT = 300.0
RISK_PCT = 0.02                # suggested risk per trade: 2% of the account
BADGE_ICON = {"GREEN": "🟢", "YELLOW": "🟡", "ORANGE": "🟠", "RED": "🔴"}
BADGE_RANK = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}


def universe(ex, top: int) -> list[dict]:
    ex.load_markets()
    tick = ex.fetch_tickers()
    rows = []
    for sym, m in ex.markets.items():
        info = m.get("info", {})
        if not (m.get("swap") and m.get("linear") and m.get("quote") == "USDT" and m.get("active")):
            continue
        if info.get("contractType") != "PERPETUAL" or info.get("underlyingType", "COIN") != "COIN":
            continue
        qv = (tick.get(sym) or {}).get("quoteVolume") or 0
        rows.append({"symbol": sym, "id": m["id"], "qv": float(qv),
                     "min_cost": (m.get("limits", {}).get("cost", {}) or {}).get("min")})
    rows.sort(key=lambda r: -r["qv"])
    return rows[:top]


def _now_ms() -> int:
    return int(time.time() * 1000)


def candles(ex, sym: str, sid: str) -> pd.DataFrame:
    f = CACHE / f"{sid}_1h.feather"
    old = pd.read_feather(f) if f.exists() else None
    since = (int(old["date"].iloc[-1].timestamp() * 1000) if old is not None and len(old)
             else _now_ms() - HOURS_NEEDED * 3_600_000)
    got = []
    # page until we reach the present (the exchange may return fewer rows than asked)
    while since < _now_ms() - 3_600_000:
        b = ex.fetch_ohlcv(sym, "1h", since=since, limit=1500)
        if not b:
            break
        got += b
        if b[-1][0] + 3_600_000 <= since:
            break
        since = b[-1][0] + 3_600_000
    new = pd.DataFrame(got, columns=["ts", "open", "high", "low", "close", "volume"])
    new["date"] = pd.to_datetime(new["ts"], unit="ms", utc=True)
    new = new.drop(columns="ts")
    df = pd.concat([old, new]) if old is not None else new
    df = df.drop_duplicates("date", keep="last").sort_values("date")
    df = df[df["date"] + pd.Timedelta(hours=1) <= pd.Timestamp.now(tz="UTC")]   # closed bars only
    df = df.tail(HOURS_NEEDED + 200).reset_index(drop=True)
    df["date"] = df["date"].astype("datetime64[ns, UTC]")   # one time unit for candles and funding (pandas 3 merge_asof)
    df.to_feather(f)
    return df


def funding(ex, sym: str, sid: str) -> pd.DataFrame:
    f = CACHE / f"{sid}_funding.feather"
    old = pd.read_feather(f) if f.exists() else None
    since = (int(old["date"].iloc[-1].timestamp() * 1000) + 1 if old is not None and len(old)
             else _now_ms() - 200 * 86_400_000)
    got = []
    while True:
        b = ex.fetch_funding_rate_history(sym, since=since, limit=1000)
        if not b:
            break
        got += [{"date": pd.Timestamp(r["timestamp"], unit="ms", tz="UTC"), "funding_rate": r["fundingRate"]} for r in b]
        if len(b) < 1000:
            break
        since = b[-1]["timestamp"] + 1
    new = pd.DataFrame(got, columns=["date", "funding_rate"])
    df = pd.concat([old, new]) if old is not None else new
    df = df.drop_duplicates("date", keep="last").sort_values("date").tail(1500).reset_index(drop=True)
    df["date"] = df["date"].astype("datetime64[ns, UTC]")
    df.to_feather(f)
    return df


def alerts_for(coin: dict, x: pd.DataFrame, book: dict, fresh: int, eff: dict | None = None) -> list[dict]:
    out = []
    L = len(x) - 1
    for name, rule in book["conditions"].items():
        if eff and name in eff:                        # effective badge: dev -> forward test
            rule = {**rule, "badge": eff[name]["badge"], "badge_why": eff[name]["why"]}
        idx = triggers(x[name])
        if len(idx) == 0 or idx[-1] < L - fresh + 1:
            continue
        i = int(idx[-1])
        sig = float(x["sigma24"].iloc[i])
        ref = float(x["open"].iloc[i + 1]) if i + 1 <= L else float(x["close"].iloc[i])
        last = float(x["close"].iloc[L])
        d = 1 if rule["direction"] == "LONG" else -1
        tgt_pct, stp_pct = rule["target_sigma"] * sig, rule["stop_sigma"] * sig
        notional = min(ACCOUNT, ACCOUNT * RISK_PCT / (stp_pct + COST_RT))
        out.append({
            "coin": coin["symbol"].split("/")[0], "symbol": coin["symbol"], "condition": name, "qv": coin["qv"],
            "why": rule["description"], "badge": rule["badge"], "badge_why": rule["badge_why"],
            "direction": rule["direction"], "trigger_bar": str(x["date"].iloc[i]),
            "hours_ago": L - i, "ref_price": ref, "last_price": last,
            "target": ref * (1 + d * tgt_pct), "stop": ref * (1 - d * stp_pct),
            "target_pct": tgt_pct * 100, "stop_pct": stp_pct * 100, "hours": rule["hours"],
            "frate": float(x["frate"].iloc[L]) if pd.notna(x["frate"].iloc[L]) else None,
            "z24": float(x["z24"].iloc[i]), "vratio": float(x["vratio"].iloc[i]),
            "notional_2pct_risk": notional, "min_cost": coin["min_cost"],
            "test": rule["test"], "random_test": rule["random_test"],
            "regimes_positive": rule["regimes_positive"],
        })
    return out


def cluster(alerts: list[dict]) -> dict[tuple, list[dict]]:
    """Group triggers of the same rule in the same hour (one market event). Adds cluster_n and cluster_rank
    (1 = most liquid coin of the event) to every alert."""
    groups: dict[tuple, list[dict]] = {}
    for a in alerts:
        groups.setdefault((a["condition"], a["trigger_bar"]), []).append(a)
    for g in groups.values():
        g.sort(key=lambda a: -a["qv"])
        for r, a in enumerate(g, 1):
            a["cluster_n"], a["cluster_rank"] = len(g), r
    return groups


def fmt_price(p: float) -> str:
    return f"{p:,.2f}" if p >= 100 else (f"{p:.4f}" if p >= 1 else f"{p:.6g}")


def render(a: dict) -> str:
    t, r = a["test"], a["random_test"]
    win = a["notional_2pct_risk"] * (a["target_pct"] / 100 - COST_RT)
    loss = a["notional_2pct_risk"] * (a["stop_pct"] / 100 + COST_RT)
    late = abs(a["last_price"] / a["ref_price"] - 1) * 100
    d = 1 if a["direction"] == "LONG" else -1
    done = d * (a["last_price"] / a["ref_price"] - 1) * 100 / a["target_pct"]
    gone = d * (a["ref_price"] / a["last_price"] - 1) * 100 / a["stop_pct"]
    warn = ("   ⚠ LATE: price already covered {:.0f}% of the way to target - the tested entry has passed\n".format(done * 100)
            if done >= 0.5 else
            "   ⚠ Price already {:.0f}% of the way to the stop\n".format(gone * 100) if gone >= 0.5 else "")
    lines = [
        f"{BADGE_ICON[a['badge']]} {a['coin']} -> {a['direction']}   ({a['condition']}, {a['hours_ago']}h ago)",
        f"   Why: {a['why']}  [24h move {a['z24']:+.1f}x normal, volume {a['vratio']:.1f}x"
        + (f", funding {a['frate'] * 100:+.4f}%" if a["frate"] is not None else "") + "]",
        f"   Entry ~{fmt_price(a['ref_price'])} (now {fmt_price(a['last_price'])}, {late:.1f}% away)"
        f" | Target {fmt_price(a['target'])} ({a['target_pct']:.1f}%)"
        f" | Stop {fmt_price(a['stop'])} ({a['stop_pct']:.1f}%) | Exit by {a['hours']}h",
        f"   Past cases 2025-26 (not used to set the rule): {t['n']} on {t['coins']} coins"
        f" | target first {t['target_first']}% | stop first {t['stop_first']}% | time exit {t['time_exit']}%",
        f"   Avg after costs {t['avg_net_pct']:+.2f}%/trade (random entries {r['avg_net_pct']:+.2f}%)"
        f" | median {t['median_net_pct']:+.2f}% | day t {t['t_day']:+.2f} | regimes {a['regimes_positive']}/4",
        f"   300 USDT, risk 2%: size {a['notional_2pct_risk']:.0f} USDT -> win ~ +{win:.1f} / loss ~ -{loss:.1f} USDT"
        + (f"  (exchange min {a['min_cost']:.0f})" if a["min_cost"] else ""),
        f"   Badge: {'; '.join(a['badge_why'])}",
    ]
    return "\n".join(lines[:3]) + "\n" + warn + "\n".join(lines[3:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=200)
    ap.add_argument("--fresh", type=int, default=3, help="show triggers from the last N closed hours")
    ap.add_argument("--all", action="store_true", help="also show RED (no-trade) conditions")
    ap.add_argument("--auto", action="store_true", help="scheduled run: log to scan_auto.log, notify new alerts")
    args = ap.parse_args()
    if args.auto:
        sys.stdout = sys.stderr = open(HERE / "scan_auto.log", "a", encoding="utf-8", buffering=1)
        print(f"\n##### auto scan {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC")

    lock = HERE / "scan.lock"                       # one scan at a time (hourly task + UI button)
    if lock.exists() and time.time() - lock.stat().st_mtime < 15 * 60:
        print("another scan is running - exit")
        return
    lock.write_text(str(os.getpid()))
    try:
        healthy = run(args)
    finally:
        lock.unlink(missing_ok=True)
    try:                                            # F1 crash-bounce alert (🟠), uses the incubator's frozen idea
        import f1_alert
        print(f"F1 crash bounce: {f1_alert.scan()}")
    except Exception as e:
        print(f"F1 alert failed: {type(e).__name__}: {e}")
    if args.auto:                                  # hourly snapshot of the Binance Web3 boards (no history API)
        try:
            import web3_recorder
            print(web3_recorder.record())
        except Exception as e:
            print(f"web3 recorder failed: {type(e).__name__}: {e}")
    if not healthy:
        sys.exit(2)                                 # visible as Last Run Result in Task Scheduler


SKIP_LIMIT = 0.10        # a scan that skips more than 10% of coins is a FAILED scan (exit code 2 + scan_health.json)


def same_time_unit(*frames: pd.DataFrame | None) -> None:
    """Cast every 'date' column to datetime64[ns, UTC] in place. pandas 3 keeps ms / us / ns units apart and
    merge_asof refuses mixed units - that silently skipped ~191 of 200 coins on 2026-10-07."""
    for f in frames:
        if f is not None and "date" in f:
            f["date"] = pd.to_datetime(f["date"], utc=True).astype("datetime64[ns, UTC]")


def run(args):
    book = json.loads((HERE / "playbook.json").read_text(encoding="utf-8"))
    eff = FW.effective_badges()
    log_window = max(args.fresh, 24)                # log every trigger of the last 24h (survives missed hours)
    CACHE.mkdir(exist_ok=True)
    ex = ccxt.binanceusdm({"enableRateLimit": True})
    coins = universe(ex, args.top)
    print(f"Scanning {len(coins)} USDT perpetuals (top by 24h volume) ...", flush=True)
    alerts, failed = [], []
    for n, c in enumerate(coins, 1):
        try:
            df = candles(ex, c["symbol"], c["id"])
            if len(df) < 800:
                continue
            age = pd.Timestamp.now(tz="UTC") - df["date"].iloc[-1]
            if age > pd.Timedelta(hours=2, minutes=15):     # stale data must never produce an alert
                failed.append(f"{c['symbol']}: stale ({age.total_seconds() / 3600:.0f}h old)")
                continue
            fu = funding(ex, c["symbol"], c["id"])
            g = regular_grid(df)
            same_time_unit(g, fu)
            x = compute_conditions(g, fu)
            alerts += alerts_for(c, x, book, log_window, eff)
        except Exception as e:                     # one bad coin must not stop the scan
            failed.append(f"{c['symbol']}: {type(e).__name__}")
        if n % 25 == 0:
            print(f"  {n}/{len(coins)}", flush=True)

    # ---- forward test: log every trigger, resolve open trades on real candles, refresh badges, notify
    new = FW.log_alerts(alerts)

    def get_candles(sym):
        sid = ex.markets[sym]["id"]
        f = CACHE / f"{sid}_1h.feather"
        if f.exists() and time.time() - f.stat().st_mtime < 3600:
            return pd.read_feather(f)
        return candles(ex, sym, sid)

    def get_funding(sym):
        sid = ex.markets[sym]["id"]
        f = CACHE / f"{sid}_funding.feather"
        return pd.read_feather(f) if f.exists() and time.time() - f.stat().st_mtime < 3600 else funding(ex, sym, sid)

    closed = FW.resolve(get_candles, get_funding)
    eff = FW.effective_badges()
    for a in alerts + new:                           # a rule killed/confirmed this hour shows its new badge now
        a["badge"], a["badge_why"] = eff[a["condition"]]["badge"], eff[a["condition"]]["why"]
    cfg = json.loads((HERE / "config.json").read_text(encoding="utf-8")) if (HERE / "config.json").exists() else {}
    sent = FW.notify_new(new, cfg.get("notify_all", False))
    print(f"forward: {len(new)} new triggers logged, {closed} trades closed, {sent} notifications")
    alerts = [a for a in alerts if a["hours_ago"] < args.fresh]
    groups = cluster(alerts)

    alerts.sort(key=lambda a: (BADGE_RANK[a["badge"]], a["hours_ago"], -a["test"]["avg_net_pct"]))
    trade = [a for a in alerts if a["badge"] != "RED"]
    red = [a for a in alerts if a["badge"] == "RED"]
    stamp = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n=== Opportunity scan {stamp} | {len(coins)} coins | triggers in last {args.fresh}h ===\n")
    if not trade:
        print("No alerts with a tested edge right now.\n")
    shown = set()
    for a in trade:
        key = (a["condition"], a["trigger_bar"])
        if key in shown:
            continue
        shown.add(key)
        g = groups[key]
        if len(g) < FW.CLUSTER_MIN:
            for x in g:
                print(render(x) + "\n")
            continue
        print(f"=== MARKET EVENT: {a['condition']} {a['direction']} on {len(g)} coins in the same hour ===\n"
              f"    This is ONE bet on the market, not {len(g)}. The two most liquid coins are shown.\n")
        for x in g[:2]:
            print(render(x) + "\n")
        print("    Also triggered: " + ", ".join(x["coin"] for x in g[2:]) + "\n")
    red_groups: dict[str, list[str]] = {}
    for a in red:
        red_groups.setdefault(a["condition"], []).append(a["coin"])
    print(f"NO TRADE (🔴 rule failed its test): {len(red)} triggers"
          + (": " + "; ".join(f"{c} x{len(v)} ({', '.join(v[:6])}{', ...' if len(v) > 6 else ''})"
                              for c, v in sorted(red_groups.items(), key=lambda kv: -len(kv[1]))) if red else ""))
    if args.all:
        for a in red:
            print("\n" + render(a))
    if failed:
        print(f"\nSkipped {len(failed)} coins (data error): {', '.join(failed[:10])}")
    (HERE / "latest_scan.json").write_text(json.dumps({"time": stamp, "coins": len(coins), "alerts": alerts},
                                                      indent=1, default=str), encoding="utf-8")
    ok = len(failed) <= SKIP_LIMIT * max(1, len(coins))
    (HERE / "scan_health.json").write_text(json.dumps(
        {"time": stamp, "coins": len(coins), "skipped": len(failed), "ok": ok, "first_errors": failed[:10]},
        indent=1), encoding="utf-8")
    if not ok:
        print(f"WARNING: scan FAILED - {len(failed)} of {len(coins)} coins skipped (limit {SKIP_LIMIT:.0%})")
    return ok


if __name__ == "__main__":
    main()
