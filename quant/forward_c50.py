r"""C50 paper forward test (Michael 2026-10-20): the registered C50 rule on live Binance 1h data, no money.

    .venv\Scripts\python.exe -m quant.forward_c50          # update (scheduled hourly: task "Quantlab C50 Forward")
    .venv\Scripts\python.exe -m quant.forward_c50 --show   # print the book

Every run recomputes the whole forward period from START from public klines (so a missed hour or a sleeping PC loses
nothing), with the exact C50 rule and costs from run_c48 (25 memes, 1h, 6x volume and trades, trail 3 ATR, fade,
72-bar cap, fee 0.05% + slippage 0.10% per side, stop +0.05%, real funding). Book: 300 USDT, 20 slots, <= 10 longs.
Open trades are marked at the last price. Output: data/forward_c50/status.json + trades.csv + run.log.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import run_c50  # noqa: F401 - sets the C50 settings (1h, 6x, 24-bar base, 72-bar cap) on run_c48
from . import run_c48 as m
from .book import START as BOOK_START, replay
from .eval_c import mins
from .paths import DATA

START = pd.Timestamp("2026-10-20 07:00")            # forward start (UTC, naive); first signals judged from here
WARM_DAYS = 35                                       # history before START for baselines and the 30-day listing rule
OUT = DATA / "forward_c50"
API = "https://fapi.binance.com"


def get(path: str):
    with urllib.request.urlopen(API + path, timeout=30) as r:
        return json.loads(r.read())


def klines(coin: str, since: pd.Timestamp) -> pd.DataFrame:
    sym = urllib.parse.quote(f"{coin}USDT")
    t0, rows = int(since.timestamp() * 1000), []
    while True:
        k = get(f"/fapi/v1/klines?symbol={sym}&interval=1h&startTime={t0}&limit=1500")
        rows += k
        if len(k) < 1500:
            break
        t0 = k[-1][0] + 1
    d = pd.DataFrame([[r[0], *map(float, (r[1], r[2], r[3], r[4], r[7], r[8]))] for r in rows],
                     columns=["t", "open", "high", "low", "close", "qvol", "count"])
    d["date"] = pd.to_datetime(d["t"], unit="ms")
    return d.drop(columns="t")


def funding(coin: str, since: pd.Timestamp) -> pd.Series:
    sym = urllib.parse.quote(f"{coin}USDT")
    f = get(f"/fapi/v1/fundingRate?symbol={sym}&startTime={int(since.timestamp() * 1000)}&limit=1000")
    return pd.Series([float(x["fundingRate"]) for x in f], index=pd.to_datetime([x["fundingTime"] for x in f], unit="ms"))


def coin_trades(coin: str, now: pd.Timestamp) -> list[dict]:
    d = klines(coin, START - pd.Timedelta(days=WARM_DAYS))
    d = d[d["date"] + pd.Timedelta(hours=1) <= now].reset_index(drop=True)      # closed bars only
    if len(d) < m.BASE + 15:
        return []
    fu = funding(coin, START - pd.Timedelta(days=1))
    sig, base_qv, atr = m.signals(d)
    o, h, l, c, qv = (d[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close", "qvol"))
    dates = d["date"].to_numpy()
    side_cost, sx = m.T.FEE + m.SLIP_MEME, m.T.STOP_EXTRA
    out, free, n = [], 0, len(d)
    for s in np.where(sig & (d["date"] >= START).to_numpy())[0]:
        e = s + 1
        if s < free or e >= n:                       # the entry bar must exist (it opens after the signal closes)
            continue
        px, safety, a = o[e], l[s], atr[s]
        if px <= safety:
            continue
        peak, x, reason, xp, is_open = -np.inf, None, None, None, False
        for j in range(e, min(e + m.HOLD, n)):
            stop = max(safety, peak - m.K_TRAIL * a)
            if l[j] <= stop:
                xp, x, reason = (o[j] if o[j] < stop else stop) * (1 - sx), j, ("trail" if stop > safety else "stop")
                break
            peak = max(peak, h[j])
            if j - e + 1 >= m.FADE_FROM and np.mean(qv[j - 3:j + 1]) < base_qv[s]:
                if j + 1 < n:
                    x, reason, xp = j + 1, "fade", o[j + 1]
                else:                                # fade decided, exit at the next open (not printed yet)
                    x, reason, xp, is_open = j, "fade (exiting next open)", c[j], True
                break
        if x is None:
            if e + m.HOLD - 1 < n:
                x, reason, xp = e + m.HOLD - 1, "time", c[e + m.HOLD - 1]
            else:
                x, reason, xp, is_open = n - 1, "open", c[n - 1]
        et = pd.Timestamp(dates[e])
        xt = pd.Timestamp(dates[x]) + pd.Timedelta(hours=1)
        f = float(fu[(fu.index > et) & (fu.index <= xt)].sum()) if len(fu) else 0.0
        cost = side_cost * (1 if is_open else 2) + (sx if reason in ("stop", "trail") else 0.0)
        gross = xp / px - 1
        out.append({"coin": coin, "side": 1, "entry_t": et, "exit_t": xt, "entry": px, "exit": xp, "reason": reason,
                    "open": is_open, "gross": gross, "funding": f, "ret": gross - cost - f,
                    "mae": float(np.min(l[e:x + 1]) / px - 1), "stop_now": float(max(safety, peak - m.K_TRAIL * a))})
        free = x + 1
    return out


def update() -> dict:
    now = pd.Timestamp(datetime.now(timezone.utc)).tz_localize(None)
    rows, errors = [], {}
    for coin in m.COINS:
        try:
            rows += coin_trades(coin, now)
        except Exception as e:  # noqa: BLE001 - one coin failing must not stop the book
            errors[coin] = f"{type(e).__name__}: {e}"
        time.sleep(0.2)
    status = {"updated": now.isoformat(timespec="minutes"), "start": START.isoformat(), "rule": "C50 (FAMILIES_C.md)",
              "errors": errors, "equity": BOOK_START, "closed": 0, "open": 0, "trades": []}
    if rows:
        t = pd.DataFrame(rows)
        far = pd.Timestamp("2100-01-01", tz="UTC")
        tb = t.assign(entry_t=pd.to_datetime(t["entry_t"], utc=True),
                      exit_t=[far if o else pd.Timestamp(x, tz="UTC") for o, x in zip(t["open"], t["exit_t"])])
        bt, curve = replay(tb, mins())
        bt["exit_t"] = pd.to_datetime(t.sort_values("entry_t")["exit_t"].to_numpy(), utc=True)
        tk = bt[bt["taken"]]
        closed, opened = tk[~tk["open"]], tk[tk["open"]]
        status.update({"equity": round(BOOK_START + float(closed["pnl"].sum()), 2),
                       "open_pnl": round(float(opened["pnl"].sum()), 2), "closed": int(len(closed)), "open": int(len(opened)),
                       "skipped_no_slot": int((~bt["taken"]).sum()),
                       "win_rate": round(float((closed["ret"] > 0).mean()), 3) if len(closed) else None,
                       "avg_ret_pct": round(float(closed["ret"].mean() * 100), 2) if len(closed) else None})
        cols = ["coin", "entry_t", "exit_t", "entry", "exit", "reason", "open", "ret", "pnl", "stake", "stop_now"]
        bt[cols].to_csv(OUT / "trades.csv", index=False)
        status["trades"] = json.loads(bt[cols].assign(entry_t=bt["entry_t"].astype(str), exit_t=bt["exit_t"].astype(str))
                                      .to_json(orient="records"))
    (OUT / "status.json").write_text(json.dumps(status, indent=1), encoding="utf-8")
    return status


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if "--show" not in sys.argv:
        s = update()
        with open(OUT / "run.log", "a", encoding="utf-8") as f:
            f.write(f"{s['updated']} equity {s['equity']} closed {s['closed']} open {s['open']} errors {len(s['errors'])}\n")
    s = json.loads((OUT / "status.json").read_text(encoding="utf-8"))
    print(json.dumps({k: v for k, v in s.items() if k != "trades"}, indent=1, ensure_ascii=False))
    for t in s["trades"]:
        print(f"  {t['coin']:10s} {t['entry_t'][:16]} {t['reason']:22s} {t['ret'] * 100:+6.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
