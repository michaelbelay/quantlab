"""Market-condition scanner (2026-10-21, Michael: "a scanner to check the market condition and tell me this bot can
trade more in the market condition or suitable for this market condition").

INFORMATION ONLY - it never switches, pauses or sizes a bot. Regime switching was tested 2026-10-07 and did not earn;
this only says what each bot did in the past in markets like today's.

Each day gets three labels, from data known at the START of the day (yesterday's close, no look-ahead):
  trend    BTC 7-day return: up > +3%, down < -3%, else sideways
  moves    BTC average absolute daily move over 14 days: calm / normal / wild (terciles of 2024-04..2026-09)
  breadth  share of the coins above their own 20-day average: weak < 35%, mixed, strong > 65%
A backtest trade belongs to the day it opened. Per label: days, trades per day, win rate, average result per trade,
and USDT per day at the live stake (fixed, no compounding): NFI 200/6, E0V1EN 100/3 per trade.

    .venv\\Scripts\\python.exe research\\fresh\\regime_scan.py history   # tables from the two 30-month backtests
    .venv\\Scripts\\python.exe research\\fresh\\regime_scan.py now       # today's labels + the matching history
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DATA = ROOT / "data" / "market" / "main" / "binance" / "futures"
OUT = HERE / "regime_history.json"
BOTS = {"NFI": (HERE / "nfi_bt_full223" / "chain_1m.json", 200 / 6),
        "E0V1EN": (HERE / "e0v1en_bt" / "chain_1m.json", 100 / 3)}
# 2026-10-21: every other saved live profile (strat_bt.py), stake = 300 USDT / its slots
for _n, _slots in (("Tandem", 6), ("FlowTrend", 6), ("V4Complacency", 2), ("MajorsTrend", 3), ("VBreak4BullCalm", 20)):
    BOTS[_n] = (HERE / "strat_bt" / _n / "chain_1m.json", 300 / _slots)
BOTS["BreakoutDay"] = (HERE / "strat_bt" / "BreakoutDay" / "chain_1m.json", 50.0)   # research rule, not live (2026-10-21)
START, END = "2024-04-01", "2026-09-30"
TREND = 0.03
BREADTH = (0.35, 0.65)


def labels(closes: pd.DataFrame, vol_cuts: tuple[float, float] | None = None) -> tuple[pd.DataFrame, tuple]:
    """closes: daily close per coin (columns), BTC included. Labels for day d use closes up to d-1."""
    btc = closes["BTC"]
    r7 = btc.pct_change(7)
    mv = btc.pct_change().abs().rolling(14).mean()
    above = (closes > closes.rolling(20).mean()).astype(float).where(closes.rolling(20).count() == 20)
    br = above.sum(axis=1) / above.notna().sum(axis=1).replace(0, float("nan"))
    f = pd.DataFrame({"r7": r7, "moves": mv, "breadth": br}).shift(1)        # known at the start of the day
    if vol_cuts is None:
        span = f.loc[START:END, "moves"]
        vol_cuts = (float(span.quantile(1 / 3)), float(span.quantile(2 / 3)))
    f["trend"] = pd.cut(f["r7"], [-9, -TREND, TREND, 9], labels=["down", "sideways", "up"]).astype(str)
    f["vol"] = pd.cut(f["moves"], [0, *vol_cuts, 9], labels=["calm", "normal", "wild"]).astype(str)
    f["width"] = pd.cut(f["breadth"], [-1, *BREADTH, 2], labels=["weak", "mixed", "strong"]).astype(str)
    return f, vol_cuts


def history_closes() -> pd.DataFrame:
    cols = {}
    for p in DATA.glob("*_USDT_USDT-1d-futures.feather"):
        d = pd.read_feather(p)
        cols[p.name.split("_USDT_USDT")[0]] = d.set_index(d["date"].dt.tz_localize(None).dt.normalize())["close"]
    return pd.DataFrame(cols).sort_index()


def trades(path: Path) -> pd.DataFrame:
    rows = [t for ch in json.loads(path.read_text(encoding="utf-8")) for t in ch["trades"]]
    if not rows:
        return pd.DataFrame()
    t = pd.DataFrame(rows)
    t["day"] = pd.to_datetime(t["open_date"], utc=True).dt.tz_localize(None).dt.normalize()
    return t[["day", "pair", "profit_ratio", "is_short"]]


def table(f: pd.DataFrame, t: pd.DataFrame, stake: float, key: str) -> list[dict]:
    days = f.groupby(key).size()
    t = t.join(f[key], on="day")
    out = []
    for lab, n in days.items():
        g = t[t[key] == lab]
        out.append({"label": lab, "days": int(n), "trades_per_day": round(len(g) / n, 2),
                    "win_rate": round(float((g.profit_ratio > 0).mean()) * 100, 1) if len(g) else None,
                    "avg_trade_pct": round(float(g.profit_ratio.mean()) * 100, 2) if len(g) else None,
                    "usdt_per_day": round(float(g.profit_ratio.sum()) * stake / n, 2),
                    "shorts_pct": round(float(g.is_short.mean()) * 100) if len(g) else None})
    return out


def history() -> int:
    f, cuts = labels(history_closes())
    res = {"period": [START, END], "vol_cuts": cuts, "trend_cut": TREND, "breadth_cuts": BREADTH, "bots": {}}
    for bot, (path, stake) in BOTS.items():
        if not path.exists():
            print(f"{bot}: no backtest yet ({path})")
            continue
        t = trades(path)
        if t.empty:
            print(f"{bot}: no trades in the backtest")
            continue
        months = {ch["tag"][:7] for ch in json.loads(path.read_text(encoding="utf-8"))}     # only months it was tested
        f2 = f.loc[START:END]
        f2 = f2[f2.index.strftime("%Y-%m").isin(months)].copy()
        f2["combo"] = f2["trend"] + " / " + f2["vol"]
        res["bots"][bot] = {k: table(f2, t, stake, k) for k in ("trend", "vol", "width", "combo")}
        res["bots"][bot]["all"] = {"days": int(len(f2)), "trades": int(len(t)),
                                   "trades_per_day": round(len(t) / len(f2), 2),
                                   "win_rate": round(float((t.profit_ratio > 0).mean()) * 100, 1),
                                   "avg_trade_pct": round(float(t.profit_ratio.mean()) * 100, 2),
                                   "usdt_per_day": round(float(t.profit_ratio.sum()) * stake / len(f2), 2)}
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    for bot, b in res["bots"].items():
        print(f"\n== {bot}  ({b['all']['trades']} trades, {b['all']['trades_per_day']} a day on average)")
        for k in ("trend", "vol", "width", "combo"):
            for r in b[k]:
                print(f"  {k:6} {r['label']:18} {r['days']:4} days  {r['trades_per_day']:5} trades/day  "
                      f"win {r['win_rate']}%  avg {r['avg_trade_pct']}%  {r['usdt_per_day']:+.2f} USDT/day  "
                      f"shorts {r['shorts_pct']}%")
    print(f"\nmoves cut-offs (BTC avg daily move, 14d): calm < {cuts[0]:.2%} < normal < {cuts[1]:.2%} < wild")
    return 0


NOW = HERE / "regime_now.json"
FAPI = "https://fapi.binance.com/fapi/v1/klines?symbol={}USDT&interval=1d&limit=40"


def live_closes() -> pd.DataFrame:
    """Daily closes for the same coins as the history (public endpoint, no keys); today's unfinished candle dropped."""
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor
    coins = sorted(p.name.split("_USDT_USDT")[0] for p in DATA.glob("*_USDT_USDT-1d-futures.feather"))

    def get(c):
        try:
            k = json.loads(urllib.request.urlopen(FAPI.format(c), timeout=20).read())
        except Exception:  # noqa: BLE001 - a delisted coin just drops out of the breadth count
            return c, None
        return c, pd.Series({pd.Timestamp(r[0], unit="ms").normalize(): float(r[4]) for r in k})
    with ThreadPoolExecutor(8) as pool:
        got = dict(x for x in pool.map(get, coins) if x[1] is not None)
    d = pd.DataFrame(got).sort_index()
    return d.iloc[:-1]                                    # yesterday is the last finished day


def now() -> int:
    h = json.loads(OUT.read_text(encoding="utf-8"))
    closes = live_closes()
    closes.loc[closes.index[-1] + pd.Timedelta(days=1)] = float("nan")       # a row for today, labelled from yesterday
    f, _ = labels(closes, tuple(h["vol_cuts"]))
    row = f.iloc[-1]
    lab = {"trend": row["trend"], "vol": row["vol"], "width": row["width"],
           "combo": f"{row['trend']} / {row['vol']}"}
    out = {"made": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "day": str(f.index[-1].date()),
           "inputs": {"btc_7d_pct": round(float(row["r7"]) * 100, 2), "btc_avg_move_pct": round(float(row["moves"]) * 100, 2),
                      "breadth_pct": round(float(row["breadth"]) * 100, 1), "coins": int(closes.notna().iloc[-2].sum())},
           "labels": lab, "cuts": {"trend": h["trend_cut"], "vol": h["vol_cuts"], "breadth": h["breadth_cuts"]},
           "period": h["period"], "bots": {}}
    for bot, b in h["bots"].items():
        out["bots"][bot] = {"all": b["all"],
                            "match": {k: next((r for r in b[k] if r["label"] == lab[k]), None) for k in lab},
                            "tables": {k: b[k] for k in ("trend", "vol", "width", "combo")}}
    NOW.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("day", "inputs", "labels")}))
    for bot, b in out["bots"].items():
        print(bot, {k: (m or {}).get("trades_per_day") for k, m in b["match"].items()}, "normal", b["all"]["trades_per_day"])
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1:]
    sys.exit(history() if cmd == ["history"] else now() if cmd == ["now"] else 2)
