r"""Spot support scanner - suggestions only, nothing is traded.

Scans every coin of configs/universe_coins.json that has a Binance SPOT /USDT pair (memes left out, DOGE kept),
finds horizontal support from daily swing lows, and ranks the coins sitting just above a strong support with room
to the next resistance. Each pick comes with plain reasons and warnings, a buy zone, a stop and a target.

This is a ranking RULE, not a tested strategy. Every top-10 pick is written once to data/support_log.jsonl and
scored afterwards on 4h candles (stop or target first; stop wins inside a candle; 30 days max), so the page shows
how the suggestions actually did. Spot public REST only, no key.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
UNIVERSE = ROOT / "configs" / "universe_coins.json"
LOG = ROOT / "data" / "support_log.jsonl"
SPOT = "https://api.binance.com"

# Michael 2026-10-16: no memes except DOGE. PAXG = gold, not a coin.
EXCLUDE = {"PUMP", "TRUMP", "PENGU", "SPX", "FARTCOIN", "WIF", "MELANIA", "USELESS", "BULLA", "1000PEPE", "PEPE",
           "SHIB", "BONK", "FLOKI", "币安人生", "龙虾", "PAXG"}
MIN_QUOTE_VOL = 250_000        # 24h spot volume in USDT; thinner coins are skipped (under 3M gets a "thin" warning)
ZONE_ATR = 1.0                 # "at support" = close at most 1 daily ATR above the level
MIN_RR = 1.5                   # top list needs target at least 1.5x as far as the stop
COST = 0.2                     # spot taker 0.1% per side, in % of the trade
MAX_DAYS = 30                  # a logged pick that hits neither stop nor target is closed at day 30
_log_lock = threading.Lock()


def _get(path: str):
    req = urllib.request.Request(SPOT + path, headers={"User-Agent": "quantlab-ui"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def _klines(sym: str, interval: str, limit: int) -> np.ndarray:
    """rows: open_time_ms, open, high, low, close, quote_volume - closed candles only."""
    k = _get(f"/api/v3/klines?symbol={sym}&interval={interval}&limit={limit}")
    a = np.array([[r[0], r[1], r[2], r[3], r[4], r[7]] for r in k], dtype=float)
    return a[:-1] if len(a) > 1 else a


def coins() -> list[str]:
    pairs = json.loads(UNIVERSE.read_text(encoding="utf-8"))["pair_whitelist"]
    return [p.split("/")[0] for p in pairs if p.split("/")[0] not in EXCLUDE]


# ------------------------------------------------------------------ indicators
def _atr(h, l, c, n=14) -> float:
    tr = np.maximum(h[1:] - l[1:], np.maximum(abs(h[1:] - c[:-1]), abs(l[1:] - c[:-1])))
    return float(tr[-n:].mean())


def _rsi(c, n=14) -> float:
    d = np.diff(c)
    up, dn = np.where(d > 0, d, 0.0), np.where(d < 0, -d, 0.0)
    au, ad = up[:n].mean(), dn[:n].mean()
    for i in range(n, len(d)):                      # Wilder smoothing
        au, ad = (au * (n - 1) + up[i]) / n, (ad * (n - 1) + dn[i]) / n
    return 100.0 if ad == 0 else float(100 - 100 / (1 + au / ad))


def _pivots(x, w: int, low: bool) -> list[int]:
    out = []
    for i in range(w, len(x) - w):
        seg = x[i - w:i + w + 1]
        if (x[i] == seg.min()) if low else (x[i] == seg.max()):
            out.append(i)
    return out


def _levels(price, idx, t, atr) -> list[dict]:
    """Cluster swing points into levels at most 0.5 ATR wide (measured from the group's lowest point, so a
    staircase of lows cannot chain into one wide band)."""
    pts = sorted(zip(price[idx], t[idx]), key=lambda z: z[0])
    groups: list[list] = []
    for p, ts in pts:
        if groups and p - groups[-1][0][0] <= 0.5 * atr:
            groups[-1].append((p, ts))
        else:
            groups.append([(p, ts)])
    return [{"level": float(np.median([g[0] for g in gr])), "touches": len(gr),
             "first": min(g[1] for g in gr), "last": max(g[1] for g in gr)} for gr in groups]


# ------------------------------------------------------------------ one coin
def analyse(coin: str, tick: dict) -> dict | None:
    sym = coin + "USDT"
    d = _klines(sym, "1d", 400)
    if len(d) < 60:
        return None
    t, o, h, l, c, qv = d.T
    px = float(tick["lastPrice"])
    atr = _atr(h, l, c)
    yr = slice(max(0, len(c) - 365), len(c))
    lo_lv = _levels(l[yr], np.array(_pivots(l[yr], 3, True), dtype=int), t[yr], atr)
    hi_lv = _levels(h[yr], np.array(_pivots(h[yr], 3, False), dtype=int), t[yr], atr)
    # support = strongest nearby level under the price (a 1-touch level only if nothing better is within 1 ATR)
    below = [v for v in lo_lv if v["level"] < px]
    if not below:
        return {"coin": coin, "price": px, "status": "no_support", "note": "price under every swing low of the last year"}
    # a real support held at least twice, at least 2 weeks apart
    strong = [v for v in below if v["touches"] >= 2 and v["last"] - v["first"] >= 14 * 86_400_000]
    near = [v for v in strong if (px - v["level"]) / atr <= ZONE_ATR]
    if near:
        sup = max(near, key=lambda v: (v["touches"], v["level"]))
    elif strong:
        sup = max(strong, key=lambda v: v["level"])
    else:
        return {"coin": coin, "price": px, "status": "no_support", "note": "no level under the price held twice in a year"}
    dist_atr = (px - sup["level"]) / atr
    stop = sup["level"] - 0.5 * atr
    above = sorted([v for v in hi_lv if v["level"] > px + 0.3 * atr], key=lambda v: v["level"])
    res = above[0]["level"] if above else float(h[yr].max())
    target = res - 0.1 * atr if res > px else px + 2 * atr
    rr = (target - px) / (px - stop) if px > stop else 0.0

    rsi = _rsi(c[-120:])
    sma50 = float(c[-50:].mean())
    sma50_prev = float(c[-55:-5].mean())
    sma200 = float(c[-200:].mean()) if len(c) >= 200 else None
    ch7 = (px / c[-7] - 1) * 100
    ch30 = (px / c[-30] - 1) * 100
    vol3, vol20 = float(qv[-3:].mean()), float(qv[-23:-3].mean())
    vol_ratio = vol3 / vol20 if vol20 else 1.0
    red3 = int((c[-3:] < o[-3:]).sum())

    k4 = _klines(sym, "4h", 30)                     # last ~5 days: is it bouncing off the level now?
    lo24 = float(k4[-6:, 3].min())
    bounce = lo24 <= sup["level"] + 0.5 * atr and px - lo24 >= 0.3 * atr
    last = k4[-1]
    hammer = (min(last[1], last[4]) - last[3]) >= 1.5 * abs(last[4] - last[1]) and last[4] >= last[1]

    reasons, warns, s = [], [], 0.0
    s += 25 * max(0.0, 1 - dist_atr / ZONE_ATR) if dist_atr <= ZONE_ATR else 0
    reasons.append(f"Price is {dist_atr:.2f} ATR ({(px / sup['level'] - 1) * 100:.1f}%) above support {sup['level']:.6g}")
    s += min(sup["touches"], 5) * 4
    span = (sup["last"] - sup["first"]) / 86_400_000
    reasons.append(f"Support held {sup['touches']} times over {span:.0f} days")
    if span >= 60:
        s += 5
    s += min(rr, 4) / 4 * 20
    if rr >= MIN_RR:
        reasons.append(f"Room to resistance {target:.6g}: reward {rr:.1f}x the risk")
    else:
        warns.append(f"Little room: resistance {target:.6g} gives only {rr:.1f}x the risk")
    if sma200 and px > sma200:
        s += 10
        reasons.append("Above its 200-day average - a pullback in an uptrend")
    elif sma200:
        warns.append("Below its 200-day average - the long trend is down")
    if sma50 > sma50_prev:
        s += 5
        reasons.append("50-day average still rising")
    if 30 <= rsi <= 45:
        s += 10
        reasons.append(f"RSI {rsi:.0f}: cooled off, not yet oversold")
    elif rsi < 30:
        s += 7
        reasons.append(f"RSI {rsi:.0f}: oversold")
    elif rsi <= 55:
        s += 4
    else:
        warns.append(f"RSI {rsi:.0f}: not a pullback, already strong")
    if bounce:
        s += 10
        reasons.append(f"Bounced {(px / lo24 - 1) * 100:.1f}% off the level in the last 24h")
    if hammer:
        s += 4
        reasons.append("Last 4h candle rejected lower prices (long lower wick)")
    if vol_ratio < 0.8:
        s += 5
        reasons.append(f"Selling is drying up: volume {vol_ratio:.1f}x its 20-day normal")
    elif vol_ratio > 1.8 and red3 >= 2:
        s -= 10
        warns.append(f"Heavy selling: volume {vol_ratio:.1f}x normal on red days")
    if ch7 < -25:
        s -= 15
        warns.append(f"Falling knife: {ch7:.0f}% in 7 days")
    if float(tick["quoteVolume"]) < 3_000_000:
        warns.append(f"Thin: {float(tick['quoteVolume']) / 1e6:.1f}M USDT traded in 24h")

    in_zone = dist_atr <= ZONE_ATR
    return {
        "coin": coin, "price": px, "status": "at_support" if in_zone else "above",
        "support": sup["level"], "touches": sup["touches"], "dist_atr": round(dist_atr, 2),
        "dist_pct": round((px / sup["level"] - 1) * 100, 2),
        "buy_lo": sup["level"], "buy_hi": sup["level"] + 0.5 * atr, "stop": stop, "target": target,
        "stop_pct": round((stop / px - 1) * 100, 2), "target_pct": round((target / px - 1) * 100, 2),
        "rr": round(rr, 2), "rsi": round(rsi, 1), "ch7": round(ch7, 1), "ch30": round(ch30, 1),
        "trend": "up" if sma200 and px > sma200 else ("down" if sma200 else "young"),
        "vol24": float(tick["quoteVolume"]), "vol_ratio": round(vol_ratio, 2), "bounce": bool(bounce),
        "score": round(max(0.0, min(100.0, s)), 1), "reasons": reasons, "warnings": warns,
        "eligible": bool(in_zone and rr >= MIN_RR and float(tick["quoteVolume"]) >= MIN_QUOTE_VOL),
    }


# ------------------------------------------------------------------ forward log
def _read_log() -> list[dict]:
    if not LOG.exists():
        return []
    return [json.loads(x) for x in LOG.read_text(encoding="utf-8").splitlines() if x.strip()]


def _resolve(e: dict) -> dict:
    """Walk 4h candles after the pick: stop first if both are touched in one candle."""
    k = _klines(e["coin"] + "USDT", "4h", 200)
    after = k[k[:, 0] > e["ts_ms"]]
    for row in after:
        if row[3] <= e["stop"]:
            return {**e, "result": "stop", "exit": e["stop"], "closed_ms": int(row[0])}
        if row[2] >= e["target"]:
            return {**e, "result": "target", "exit": e["target"], "closed_ms": int(row[0])}
    if len(after) and (after[-1][0] - e["ts_ms"]) / 86_400_000 >= MAX_DAYS:
        return {**e, "result": "time", "exit": float(after[-1][4]), "closed_ms": int(after[-1][0])}
    return {**e, "now": float(after[-1][4]) if len(after) else e["entry"]}


def update_log(top: list[dict], now_ms: int) -> list[dict]:
    with _log_lock:
        rows = _read_log()
        rows = [_resolve(r) if "result" not in r else r for r in rows]
        open_coins = {r["coin"] for r in rows if "result" not in r}
        for i, p in enumerate(top):
            if p["coin"] not in open_coins:
                rows.append({"ts_ms": now_ms, "coin": p["coin"], "rank": i + 1, "score": p["score"],
                             "entry": p["price"], "stop": p["stop"], "target": p["target"], "rr": p["rr"]})
        LOG.parent.mkdir(parents=True, exist_ok=True)
        LOG.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    for r in rows:
        x = r.get("exit", r.get("now", r["entry"]))
        r["ret_pct"] = round((x / r["entry"] - 1) * 100 - COST, 2)
    return rows


# ------------------------------------------------------------------ whole scan
def build() -> dict:
    t0 = time.time()
    ticks = {x["symbol"]: x for x in _get("/api/v3/ticker/24hr") if x["symbol"].endswith("USDT")}
    want = coins()
    have = [c for c in want if c + "USDT" in ticks]
    no_spot = [c for c in want if c + "USDT" not in ticks]
    thin = [c for c in have if float(ticks[c + "USDT"]["quoteVolume"]) < MIN_QUOTE_VOL]
    scan = [c for c in have if c not in thin]

    def one(c):
        try:
            return analyse(c, ticks[c + "USDT"])
        except Exception as e:  # noqa: BLE001 - one bad coin never stops the scan
            return {"coin": c, "status": "error", "note": f"{type(e).__name__}: {e}"}

    with ThreadPoolExecutor(8) as ex:
        rows = [r for r in ex.map(one, scan) if r]
    ok = [r for r in rows if r.get("status") in ("at_support", "above")]
    top = sorted([r for r in ok if r["eligible"]], key=lambda r: -r["score"])[:10]
    near = sorted([r for r in ok if r["status"] == "at_support"], key=lambda r: -r["score"])

    btc = next((r for r in ok if r["coin"] == "BTC"), None)
    bd = _klines("BTCUSDT", "1d", 30)
    btc20 = (float(ticks["BTCUSDT"]["lastPrice"]) / bd[-20, 4] - 1) * 100
    now_ms = int(time.time() * 1000)
    log = update_log(top, now_ms)
    closed = [r for r in log if "result" in r]
    return {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seconds": round(time.time() - t0, 1),
        "universe": len(want), "scanned": len(scan), "no_spot": no_spot, "thin": thin,
        "errors": [r for r in rows if r.get("status") == "error"],
        "market": {"btc_20d": round(btc20, 2), "btc_trend": btc["trend"] if btc else None,
                   "note": ("BTC is falling over 20 days: supports break more often in a falling market."
                            if btc20 < 0 else "BTC is rising over 20 days: pullbacks to support hold more often in a rising market.")},
        "top": top, "near": near,
        "log": sorted(log, key=lambda r: -r["ts_ms"])[:60],
        "log_stats": {"picks": len(log), "closed": len(closed),
                      "targets": sum(r["result"] == "target" for r in closed),
                      "stops": sum(r["result"] == "stop" for r in closed),
                      "timed": sum(r["result"] == "time" for r in closed),
                      "avg_closed": round(float(np.mean([r["ret_pct"] for r in closed])), 2) if closed else None},
        "rules": {"zone_atr": ZONE_ATR, "min_rr": MIN_RR, "min_vol": MIN_QUOTE_VOL, "cost_pct": COST, "max_days": MAX_DAYS},
    }


if __name__ == "__main__":
    out = build()
    print(f"{out['scanned']} scanned in {out['seconds']}s, {len(out['near'])} at support, top {len(out['top'])}")
    for i, r in enumerate(out["top"], 1):
        print(f"{i:>2} {r['coin']:<8} score {r['score']:>5}  px {r['price']:.6g} sup {r['support']:.6g} "
              f"stop {r['stop_pct']}% tgt {r['target_pct']}% rr {r['rr']}  {'; '.join(r['reasons'][:3])}")
    print("no spot:", out["no_spot"]); print("thin:", out["thin"]); print("errors:", out["errors"][:5])
