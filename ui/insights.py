r"""Insights: market context for the coins the live bot holds, to support Michael's own calls (decision log).

    build(fetch, symbols) -> dict          GET /api/insights?symbols=BTCUSDT,XLMUSDT,...

Binance USDT-M public data only (no key). Per coin: price change 4 h / 24 h, open interest change 4 h / 24 h (money in
open positions), funding rate, 24 h volume vs the previous 7 days, taker-buy share, and the long/short account ratio.

The plain-language readings below are the usual way traders read these numbers. They are INFORMATION, not tested
signals: none of them has been through a registered test. The decision log measures whether acting on them helps.
"""
from __future__ import annotations

import re
import time
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor

SYM = re.compile(r"^[0-9A-Z一-鿿]{2,30}USDT$")
_cache: dict[str, tuple[float, dict]] = {}


def _pct(a: float, b: float) -> float | None:
    return (a / b - 1) * 100 if b else None


def coin(fetch, sym: str) -> dict:
    hit = _cache.get(sym)
    if hit and time.time() - hit[0] < 120:
        return hit[1]
    out: dict = {"symbol": sym}
    q = quote(sym)                                     # coins with non-ASCII names
    try:
        k = fetch(f"/fapi/v1/klines?symbol={q}&interval=1h&limit=193", ttl=120)       # 8 days of 1 h
        c = [float(r[4]) for r in k]
        qv = [float(r[7]) for r in k]
        tb = [float(r[10]) for r in k]                                                 # taker buy quote volume
        out["price"] = c[-1]
        out["chg_4h"] = _pct(c[-1], c[-5])
        out["chg_24h"] = _pct(c[-1], c[-25])
        v24, prev = sum(qv[-24:]), qv[:-24]
        out["vol_24h"] = v24
        out["vol_ratio"] = v24 / (sum(prev) / len(prev) * 24) if prev and sum(prev) else None
        out["taker_buy"] = sum(tb[-24:]) / v24 * 100 if v24 else None
    except Exception as e:
        out["error"] = f"price: {type(e).__name__}"
    try:
        h = fetch(f"/futures/data/openInterestHist?symbol={q}&period=1h&limit=25", ttl=120)
        v = [float(r["sumOpenInterestValue"]) for r in h]
        out["oi_usd"] = v[-1]
        out["oi_4h"] = _pct(v[-1], v[-5]) if len(v) >= 5 else None
        out["oi_24h"] = _pct(v[-1], v[0]) if len(v) >= 25 else None
    except Exception:
        out["oi_24h"] = None
    try:
        out["funding"] = float(fetch(f"/fapi/v1/premiumIndex?symbol={q}", ttl=60)["lastFundingRate"]) * 100
    except Exception:
        out["funding"] = None
    try:
        r = fetch(f"/futures/data/globalLongShortAccountRatio?symbol={q}&period=1h&limit=1", ttl=300)
        out["ls_ratio"] = float(r[-1]["longShortRatio"]) if r else None
    except Exception:
        out["ls_ratio"] = None
    out["reads"] = reads(out)
    _cache[sym] = (time.time(), out)
    return out


def reads(x: dict) -> list[dict]:
    """[{text, lean}] lean = +1 leans up, -1 leans down, 0 neutral / crowding warning (see 'crowd')."""
    r = []
    p, o = x.get("chg_24h"), x.get("oi_24h")
    if p is not None and o is not None:
        if abs(o) < 2:
            r.append({"text": "open interest flat: no big new money either way", "lean": 0})
        elif p > 0 and o > 0:
            r.append({"text": "price and open interest up: new money is entering the rise", "lean": 1})
        elif p > 0 and o < 0:
            r.append({"text": "price up, open interest down: shorts closing, few new buyers", "lean": 0})
        elif p < 0 and o > 0:
            r.append({"text": "price down, open interest up: new shorts are piling in", "lean": -1})
        else:
            r.append({"text": "price and open interest down: longs are leaving", "lean": -1})
    f = x.get("funding")
    if f is not None:
        if f >= 0.03:
            r.append({"text": f"funding {f:.3f}%: longs are crowded and paying a lot", "lean": 0, "crowd": "long"})
        elif f <= -0.01:
            r.append({"text": f"funding {f:.3f}%: shorts are crowded and paying", "lean": 0, "crowd": "short"})
    v = x.get("vol_ratio")
    if v is not None:
        if v >= 1.8:
            r.append({"text": f"volume {v:.1f}x its usual: busy, attention is high", "lean": 0})
        elif v <= 0.6:
            r.append({"text": f"volume {v:.1f}x its usual: interest is fading", "lean": 0})
    t = x.get("taker_buy")
    if t is not None and (t >= 55 or t <= 45):
        r.append({"text": f"{t:.0f}% of volume was aggressive buying: buyers in control" if t >= 55
                  else f"only {t:.0f}% of volume was aggressive buying: sellers in control",
                  "lean": 1 if t >= 55 else -1})
    ls = x.get("ls_ratio")
    if ls is not None:
        if ls >= 2.5:
            r.append({"text": f"{ls:.1f} long accounts per short: the crowd is heavily long", "lean": 0, "crowd": "long"})
        elif ls <= 0.8:
            r.append({"text": f"{ls:.1f} long accounts per short: the crowd is short", "lean": 0, "crowd": "short"})
    return r


def for_side(x: dict, side: str | None) -> dict | None:
    """Rough tilt for an open position: how many readings point with it vs against it. Not a tested signal."""
    if side not in ("long", "short"):
        return None
    s = 1 if side == "long" else -1
    w = sum(1 for q in x.get("reads", []) if q["lean"] * s > 0)
    a = sum(1 for q in x.get("reads", []) if q["lean"] * s < 0 or q.get("crowd") == side)
    return {"with": w, "against": a,
            "word": "supports" if w > a else "against" if a > w else "mixed"}


def build(fetch, symbols: list[str], sides: dict[str, str] | None = None) -> dict:
    syms = [s for s in dict.fromkeys(["BTCUSDT", *symbols]) if SYM.match(s)][:25]
    with ThreadPoolExecutor(6) as pool:
        rows = list(pool.map(lambda s: coin(fetch, s), syms))
    sides = sides or {}
    for x in rows:
        x["side"] = sides.get(x["symbol"])
        x["tilt"] = for_side(x, x["side"])
    return {"at": int(time.time() * 1000), "rows": rows,
            "note": "Information, not tested signals. The decision log measures whether acting on it helps."}
