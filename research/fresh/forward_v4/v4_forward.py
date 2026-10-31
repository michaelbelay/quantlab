"""V4 "complacency short" - forward test on live data (FORWARD_V4_2026-10-14.md). Paper only: no orders, no bot.

Rule (frozen = research/fresh/batch_v.py v4((1.5, 7)), REGISTER_V_2026-10-13.md):
  Daily close (00:00 UTC). Deribit DVOL z(90d) <= -1.5 AND 10-day return < 0  ->  short that coin's Binance USD-M perp
  at the next day's 00:00 1h open. Exit after 7 days (close of the 168th 1h bar) or stop at entry x (1 + 3 x sigma),
  sigma = sd of the last 720 1h log returns x sqrt(24). Costs 0.10%/side + real funding. BTC and ETH, one trade per
  coin until it closes. Account: 300 USDT, 2 slots of equity/2, 1x.

Every run rebuilds everything from the forward start using public data (Binance fapi klines + fundingRate, Deribit
get_volatility_index_data), so a missed run (sleep, reboot) loses nothing: the next run replays the closed bars.

    .venv\\Scripts\\python.exe research\\fresh\\forward_v4\\v4_forward.py          # update state.json + trades.csv
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
START = pd.Timestamp("2026-10-15 00:00", tz="UTC")     # first possible entry; signals from the 2026-10-14 close on
COINS = ("BTC", "ETH")
K, HOLD_DAYS, STOP_MULT, SIDE, SLOTS, ACCOUNT = 1.5, 7, 3.0, 0.001, 2, 300.0


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


def klines(coin: str, since: pd.Timestamp) -> pd.DataFrame:
    """Closed 1h futures candles from `since`, indexed by open time."""
    rows, t = [], ms(since)
    while True:
        r = get(f"https://fapi.binance.com/fapi/v1/klines?symbol={coin}USDT&interval=1h&startTime={t}&limit=1500")
        rows += r
        if len(r) < 1500:
            break
        t = r[-1][0] + 1
    x = pd.DataFrame([row[:5] + [row[6]] for row in rows], columns=["t", "open", "high", "low", "close", "close_t"])
    x = x.astype({"open": float, "high": float, "low": float, "close": float})
    x = x[x.close_t < time.time() * 1000]                      # closed bars only
    x.index = pd.to_datetime(x.t, unit="ms", utc=True)
    return x[["open", "high", "low", "close"]].asfreq("1h").ffill()


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


def dvol(coin: str, since: pd.Timestamp) -> pd.Series:
    """Daily DVOL closes, labelled by day (value at the end of that day); only finished days."""
    rows, end, start = [], int(time.time() * 1000), ms(since)
    while end > start:
        r = get(f"https://www.deribit.com/api/v2/public/get_volatility_index_data?currency={coin}"
                f"&start_timestamp={start}&end_timestamp={end}&resolution=1D")["result"]
        if not r["data"]:
            break
        rows += r["data"]
        nxt = r.get("continuation")
        if not nxt or nxt >= end:
            break
        end = nxt
    s = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close"]).drop_duplicates("t")
    s.index = pd.to_datetime(s.t, unit="ms", utc=True)
    s = s.sort_index()["close"]
    today = pd.Timestamp.now(tz="UTC").normalize()
    return s[s.index < today]


# ------------------------------------------------------------------ the rule (same arithmetic as batch_v.py)
def features(x: pd.DataFrame, dv: pd.Series) -> pd.DataFrame:
    dc = x["close"].resample("1D").last()
    dc = dc[dc.index + pd.Timedelta(days=1) <= x.index[-1] + pd.Timedelta(hours=1)]   # finished days only
    d = dv.reindex(dc.index)
    z = (d - d.rolling(90, min_periods=60).mean()) / d.rolling(90, min_periods=60).std()
    r10 = np.log(dc) - np.log(dc).shift(10)
    return pd.DataFrame({"dvol": d, "z": z, "r10": r10, "close": dc})


def sigma24(x: pd.DataFrame) -> np.ndarray:
    return (np.log(x["close"]).diff().rolling(720, min_periods=500).std() * np.sqrt(24)).to_numpy()


def run_coin(coin: str, x: pd.DataFrame, fu: pd.Series, fe: pd.DataFrame, start: pd.Timestamp) -> list[dict]:
    """Signals -> trades. Closed trades have an exit; a trade whose 7 days are not over yet is returned as open."""
    sg = sigma24(x)
    o, h, c = (x[k].to_numpy() for k in ("open", "high", "close"))
    fh = fu.reindex(x.index).fillna(0.0).to_numpy()
    out, busy_until = [], pd.Timestamp("2000-01-01", tz="UTC")
    sig = fe[(fe.z <= -K) & (fe.r10 < 0)]
    for day, row in sig.iterrows():
        t = day + pd.Timedelta(days=1)
        if t < start or t <= busy_until or t not in x.index:
            continue
        i = int(x.index.searchsorted(t))
        if not np.isfinite(sg[i - 1]):
            continue
        e = o[i]
        stop = e * (1 + STOP_MULT * sg[i - 1])
        j_full = i + HOLD_DAYS * 24 - 1
        j = min(j_full, len(x) - 1)
        k_end, px, why = None, None, None
        for k in range(i, j + 1):
            if h[k] >= stop:
                k_end, px, why = k, (max(o[k], stop) if k > i else stop), "stop"
                break
        if k_end is None and j == j_full:
            k_end, px, why = j, c[j], "7 days"
        tr = {"coin": coin, "signal_day": str(day.date()), "dvol": round(float(row.dvol), 2),
              "z": round(float(row.z), 2), "r10_pct": round(float(row.r10) * 100, 2),
              "t_in": str(x.index[i]), "entry": e, "stop": round(stop, 6), "sigma24_pct": round(sg[i - 1] * 100, 3)}
        if k_end is None:
            tr.update(status="open", last=float(c[-1]), bars=len(x) - i,
                      upnl_pct=round((-(c[-1] / e - 1) - 2 * SIDE + fh[i + 1:].sum()) * 100, 3))
            out.append(tr)
            break                                              # busy until it closes
        net = -(px / e - 1) - 2 * SIDE + fh[i + 1:k_end + 1].sum()
        tr.update(status="closed", t_out=str(x.index[k_end]), exit=float(px), why=why, ret_pct=round(net * 100, 3))
        out.append(tr)
        busy_until = x.index[k_end]
    return out


def book(closed: pd.DataFrame, start: float = ACCOUNT, slots: int = SLOTS):
    """Same account model as research/fresh/batch_b.py book()."""
    taken = []
    for r in closed.sort_values("t_in").itertuples():
        t_in, t_out = pd.Timestamp(r.t_in), pd.Timestamp(r.t_out)
        if sum(1 for t_o, _ in taken if t_o > t_in) >= slots:
            continue
        eq_in = start + sum(p for t_o, p in taken if t_o <= t_in)
        taken.append((t_out, eq_in / slots * r.ret_pct / 100))
    if not taken:
        return start, 0.0
    cur = pd.Series([p for _, p in taken], index=[t for t, _ in taken]).sort_index().cumsum() + start
    return float(cur.iloc[-1]), float((1 - cur / cur.cummax().clip(lower=start)).max())


def main():
    hist0 = START - pd.Timedelta(days=200)                     # 90d z + 720h sigma need history before the start
    trades, signals = [], {}
    for coin in COINS:
        x, fu, dv = klines(coin, hist0), funding(coin, START - pd.Timedelta(days=1)), dvol(coin, hist0)
        fe = features(x, dv)
        last = fe.dropna().iloc[-1]
        signals[coin] = {"day": str(fe.dropna().index[-1].date()), "dvol": round(float(last.dvol), 2),
                         "z": round(float(last.z), 2), "r10_pct": round(float(last.r10) * 100, 2),
                         "signal": bool(last.z <= -K and last.r10 < 0)}
        trades += run_coin(coin, x, fu, fe, START)
    df = pd.DataFrame(trades)
    closed = df[df.status == "closed"] if len(df) else df
    eq, dd = book(closed) if len(closed) else (ACCOUNT, 0.0)
    rets = closed.ret_pct if len(closed) else pd.Series(dtype=float)
    state = {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "forward_start": str(START),
             "rule": f"DVOL z90 <= -{K} and 10d return < 0 -> short {HOLD_DAYS}d, stop {STOP_MULT}x sigma24; BTC+ETH",
             "latest_close": signals, "closed_trades": int(len(closed)),
             "avg_pct": round(float(rets.mean()), 3) if len(rets) else None,
             "pf": round(float(rets[rets > 0].sum() / max(1e-9, -rets[rets < 0].sum())), 2) if len(rets) else None,
             "account": round(eq, 2), "max_drop_pct": round(dd * 100, 1),
             "open": df[df.status == "open"].to_dict("records") if len(df) else [],
             "trades": closed.to_dict("records") if len(closed) else []}
    (HERE / "state.json").write_text(json.dumps(state, indent=1, default=str), encoding="utf-8")
    if len(df):
        df.to_csv(HERE / "trades.csv", index=False)
    with open(HERE / "run.log", "a", encoding="utf-8") as f:
        f.write(f"{state['updated']} closed {state['closed_trades']} open {len(state['open'])} account {state['account']}"
                f" | " + " ".join(f"{c} z {s['z']:+.2f} r10 {s['r10_pct']:+.1f}%{' SIGNAL' if s['signal'] else ''}"
                                  for c, s in signals.items()) + "\n")
    print(json.dumps({k: v for k, v in state.items() if k != "trades"}, indent=1, default=str))


if __name__ == "__main__":
    main()
