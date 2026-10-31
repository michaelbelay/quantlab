"""Bear batch - 10 new ideas on the NFIFull coins (2026-10-24). Rule: REGISTER_BEAR_BATCH_2026-10-24.md.

    .venv\\Scripts\\python.exe research\\fresh\\bear_batch.py

Output: research/fresh/bear_batch/trades_<idea>.csv, report.json, REPORT.md; result appended to the register.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / "bear_batch"
DATA = ROOT / "data" / "market" / "main" / "binance" / "futures"
COST = 0.002
START, END, MID = pd.Timestamp("2024-04-01", tz="UTC"), pd.Timestamp("2026-10-01", tz="UTC"), pd.Timestamp("2025-07-01", tz="UTC")
PAIRS = json.loads((HERE / "strat_bt" / "CrashShort" / "config.json").read_text())["exchange"]["pair_whitelist"]

# name: (side, stop, target, hold hours)
IDEAS = {
    "rally_short": ("short", 0.05, 0.06, 48), "retest_short": ("short", 0.04, 0.08, 48),
    "fade_breakout": ("short", 0.04, 0.04, 24), "crash_bounce": ("long", 0.06, 0.05, 24),
    "flush_long": ("long", 0.10, 0.08, 72), "weak_short": ("short", 0.06, 0.10, 72),
    "leader_long": ("long", 0.06, 0.10, 72), "pump_fade": ("short", 0.08, 0.12, 72),
    "bear_rally_short": ("short", 0.05, 0.06, 48),
}


def rsi(c: pd.Series, n: int = 14) -> pd.Series:
    d = c.diff()
    up, dn = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(), (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def load(pair: str) -> pd.DataFrame | None:
    f = DATA / f"{pair.split('/')[0]}_USDT_USDT-1h-futures.feather"
    if not f.exists():
        return None
    df = pd.read_feather(f).set_index("date").sort_index()
    return df[df.index >= START - pd.Timedelta(days=60)]


BTC_BEAR = BTC_RET168 = pd.Series(dtype=float)


def signals(df: pd.DataFrame) -> tuple[dict[str, pd.Series], pd.Series]:
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]
    e50, e200, r = c.ewm(span=50, adjust=False).mean(), c.ewm(span=200, adjust=False).mean(), rsi(c)
    ret24, ret168 = c / c.shift(24) - 1, c / c.shift(168) - 1
    bear = BTC_BEAR.reindex(df.index).fillna(False).astype(bool)
    rel = ret168 - BTC_RET168.reindex(df.index)
    vol24 = v.shift(1).rolling(24).mean()
    level = l.shift(25).rolling(168).min()
    rally = (c < e200) & (e50 < e200) & (r >= 70)
    return {
        "rally_short": rally,
        "retest_short": (l.rolling(24).min() < level * 0.98) & (c >= level * 0.995) & (c <= level * 1.02) & (c < df["open"]),
        "fade_breakout": (c > h.shift(1).rolling(24).max()) & (v > 2 * vol24) & (ret24 > 0.03) & bear,
        "crash_bounce": (c < l.shift(1).rolling(24).min()) & (v > 2 * vol24) & (ret24 < -0.03),
        "flush_long": (ret24 <= -0.15) & (r <= 20),
        "weak_short": bear & (rel <= -0.15) & (c < e50) & r.between(40, 60),
        "leader_long": bear & (rel >= 0.15) & (c > e50) & r.between(50, 70),
        "pump_fade": (ret24 >= 0.25) & (c < l.shift(1)),
        "bear_rally_short": rally & bear,
    }, bear


def simulate(df: pd.DataFrame, sig: pd.Series, side: str, sl: float, tp: float, hold: int) -> list[tuple]:
    o = df.index
    c, h, l = df["close"].to_numpy(), df["high"].to_numpy(), df["low"].to_numpy()
    idx = np.flatnonzero(sig.to_numpy() & (o >= START) & (o < END))
    res, busy = [], -1
    for i in idx:
        if i <= busy or i + 1 >= len(c):
            continue
        e, out, j = c[i], None, i
        for j in range(i + 1, min(i + hold, len(c) - 1) + 1):
            if side == "long":
                if l[j] <= e * (1 - sl):
                    out = -sl
                elif h[j] >= e * (1 + tp):
                    out = tp
            else:
                if h[j] >= e * (1 + sl):
                    out = -sl
                elif l[j] <= e * (1 - tp):
                    out = tp
            if out is not None:
                break
        if out is None:
            out = (c[j] / e - 1) * (1 if side == "long" else -1)
        res.append((o[i], o[j], out - COST))
        busy = j
    return res


def stats(t: pd.DataFrame) -> dict:
    if not len(t):
        return {"trades": 0}
    pm = t.groupby(t["open"].dt.strftime("%Y-%m"))["net"].sum()
    return {"trades": int(len(t)), "win": round(float((t.net > 0).mean() * 100), 1), "avg": round(float(t.net.mean() * 100), 3),
            "months_pos": f"{int((pm > 0).sum())}/{len(pm)}", "months_pos_pct": round(float((pm > 0).mean() * 100), 1),
            "usdt_50": round(float(t.net.sum() * 50), 0)}


def basket(closes: pd.DataFrame, bear_day: pd.Series) -> dict:
    mondays = closes.index[(closes.index.dayofweek == 0) & (closes.index.hour == 0) & (closes.index >= START) & (closes.index < END)]
    rows = []
    for t0 in mondays:
        t1 = t0 + pd.Timedelta(hours=168)
        if t1 not in closes.index:
            continue
        mom = (closes.loc[t0] / closes.loc[t0 - pd.Timedelta(days=30)] - 1).dropna() if t0 - pd.Timedelta(days=30) in closes.index else pd.Series(dtype=float)
        fwd = (closes.loc[t1] / closes.loc[t0] - 1)
        mom = mom[fwd.reindex(mom.index).notna()]
        if len(mom) < 40:
            continue
        top, bot = mom.nlargest(10).index, mom.nsmallest(10).index
        lo, sh = fwd[top].mean() - COST, -fwd[bot].mean() - COST
        rows.append({"week": t0, "half": "A" if t0 < MID else "B", "ls": (lo + sh) / 2, "short_bear": sh if bool(bear_day.get(t0, False)) else np.nan})
    w = pd.DataFrame(rows)
    out = {}
    for col in ("ls", "short_bear"):
        d = w.dropna(subset=[col])
        out[col] = {"weeks": int(len(d)), "avg_week_pct": round(float(d[col].mean() * 100), 2), "weeks_pos_pct": round(float((d[col] > 0).mean() * 100), 1),
                    "by_half": {hh: round(float(g[col].mean() * 100), 2) for hh, g in d.groupby("half")}}
        a = out[col]["by_half"]
        out[col]["verdict"] = "🟡" if len(a) == 2 and min(a.values()) > 0 and out[col]["weeks_pos_pct"] >= 55 else "🔴"
    return out


def main() -> None:
    global BTC_BEAR, BTC_RET168
    OUT.mkdir(exist_ok=True)
    btc = pd.read_feather(DATA / "BTC_USDT_USDT-1h-futures.feather").set_index("date").sort_index()
    BTC_BEAR = (btc["close"] < btc["close"].rolling(1200).mean()).shift(1)
    BTC_RET168 = btc["close"] / btc["close"].shift(168) - 1
    trades = {k: [] for k in IDEAS}
    closes = {}
    for n, p in enumerate(PAIRS):
        df = load(p)
        if df is None or len(df) < 500:
            continue
        closes[p] = df["close"]
        sigs, bear = signals(df)
        for k, (side, sl, tp, hold) in IDEAS.items():
            for a, b, net in simulate(df, sigs[k].fillna(False).astype(bool), side, sl, tp, hold):
                trades[k].append((p, a, b, net, bool(bear.loc[a])))
        if n % 40 == 0:
            print(f"  {n}/{len(PAIRS)} coins", flush=True)
    rep, md = {}, ["# Bear batch result (automatic, rules unchanged)", "",
                    "| # | idea | trades | win | avg net | 2024-04..25-06 | 2025-07..26-09 | months + | bear days avg (A / B, trades) | USDT @50/trade | verdict |",
                    "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, k in enumerate(IDEAS, 1):
        t = pd.DataFrame(trades[k], columns=["pair", "open", "close", "net", "bear"])
        t.to_csv(OUT / f"trades_{k}.csv", index=False)
        A, B = t[t.open < MID], t[t.open >= MID]
        s, sa, sb = stats(t), stats(A), stats(B)
        ba, bb_ = stats(A[A.bear]), stats(B[B.bear])
        cand = s["trades"] >= 300 and sa.get("avg", -9) >= 0.30 and sb.get("avg", -9) >= 0.30 and s.get("months_pos_pct", 0) >= 60
        bear_ok = ba.get("trades", 0) >= 100 and bb_.get("trades", 0) >= 100 and ba.get("avg", -9) >= 0.30 and bb_.get("avg", -9) >= 0.30
        v = "🟡 candidate" if cand else "🟡 bear specialist" if bear_ok else "🔴"
        rep[k] = {"all": s, "A": sa, "B": sb, "bear_A": ba, "bear_B": bb_, "verdict": v}
        md.append(f"| {i} | {k} | {s.get('trades', 0)} | {s.get('win', '-')}% | {s.get('avg', '-')}% | {sa.get('avg', '-')}% | {sb.get('avg', '-')}% | "
                  f"{s.get('months_pos', '-')} | {ba.get('avg', '-')}% / {bb_.get('avg', '-')}% ({ba.get('trades', 0)}/{bb_.get('trades', 0)}) | {s.get('usdt_50', 0):+.0f} | {v} |")
    rep["xs_basket"] = basket(pd.DataFrame(closes), BTC_BEAR)
    for col, name in (("ls", "10 xs_basket long top10 / short bottom10"), ("short_bear", "10b short bottom10, BTC-bear weeks")):
        x = rep["xs_basket"][col]
        md.append(f"| {name} | {x['weeks']} weeks | {x['weeks_pos_pct']}% weeks + | {x['avg_week_pct']}%/week | "
                  f"{x['by_half'].get('A', '-')}% | {x['by_half'].get('B', '-')}% | | | | {x['verdict']} |")
    (OUT / "report.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    text = "\n".join(md) + "\n"
    (OUT / "REPORT.md").write_text(text, encoding="utf-8")
    (HERE / "REGISTER_BEAR_BATCH_2026-10-24.md").open("a", encoding="utf-8").write("\n" + text.replace("# Bear batch result", "## Result"))
    print(text, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
