"""Switcher-3 (2026-11-12): the weekly Switcher with FlowTrend as a third book. Rule: REGISTER_SWITCHER3_2026-11-12.md.

    .venv\\Scripts\\python.exe research\\fresh\\switcher3.py

Output: research/fresh/switcher3/{weeks.csv, trades_F.csv, result.json, REPORT.md}; result appended to the register.
Report-only. Nothing trades.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
import sys  # noqa: E402
sys.path.insert(0, str(HERE))
import bear_batch as bb  # noqa: E402

OUT = HERE / "switcher3"
FLOW = bb.ROOT / "data" / "market" / "flow"
S, E = pd.Timestamp("2022-02-07", tz="UTC"), pd.Timestamp("2026-10-01", tz="UTC")
bb.START, bb.END = S, E
Z_MIN, TREND_H, WIN_H, NORM_H, NORM_MIN, HOLD_H, STOP_K, COOLDOWN_H, TOP_N = 2.0, 240, 24, 720, 500, 48, 2.0, 24, 10
COST = bb.COST
BOOKS3, BOOKS2 = ["R", "F", "M"], ["R", "M"]


def wk(s: pd.Series) -> pd.Series:
    return (s - pd.to_timedelta(s.dt.dayofweek, unit="D")).dt.normalize()


def load_all() -> dict[str, pd.DataFrame]:
    frames = {}
    for p in bb.PAIRS:
        f = bb.DATA / f"{p.split('/')[0]}_USDT_USDT-1h-futures.feather"
        if not f.exists():
            continue
        df = pd.read_feather(f).set_index("date").sort_index()
        if len(df) >= 500:
            frames[p] = df
    return frames


def top10_by_month(frames: dict[str, pd.DataFrame]) -> dict[pd.Timestamp, set[str]]:
    """month start -> coins in the top 10 by the PREVIOUS calendar month's traded value (close x volume)."""
    val = {p: (d["close"] * d["volume"]).resample("MS").agg(["sum", "count"]) for p, d in frames.items()}
    months = sorted({m for v in val.values() for m in v.index})
    out = {}
    for prev, m in zip(months[:-1], months[1:]):
        rows = {p: v.loc[prev, "sum"] for p, v in val.items() if prev in v.index and v.loc[prev, "count"] >= 480}
        out[m] = set(sorted(rows, key=rows.get, reverse=True)[:TOP_N])
    return out


def f_trades(p: str, df: pd.DataFrame, top: dict) -> list[tuple]:
    f = FLOW / f"{p.split('/')[0]}.feather"
    if not f.exists():
        return []
    q = pd.read_feather(f).drop_duplicates("date").set_index("date")
    qv = q["quote_volume"].reindex(df.index).fillna(0.0)
    tbq = q["taker_buy_quote"].reindex(df.index).fillna(0.0)
    share = tbq.rolling(WIN_H).sum() / qv.rolling(WIN_H).sum().replace(0, np.nan)
    z = ((share - share.rolling(NORM_H, min_periods=NORM_MIN).mean()) / share.rolling(NORM_H, min_periods=NORM_MIN).std()).to_numpy()
    lc = np.log(df["close"])
    sig24 = (lc.diff().rolling(NORM_H, min_periods=NORM_MIN).std() * np.sqrt(24)).to_numpy()
    r10 = (lc - lc.shift(TREND_H)).to_numpy()
    ok = np.isfinite(sig24) & (sig24 > 0) & (df["volume"].to_numpy() > 0) & np.isfinite(z)
    raw = {1: ok & (r10 > 0) & (z >= Z_MIN), -1: ok & (r10 < 0) & (z <= -Z_MIN)}
    idx = df.index
    months = idx.to_period("M").to_timestamp().tz_localize("UTC")
    c, h, l = df["close"].to_numpy(), df["high"].to_numpy(), df["low"].to_numpy()
    sigs = []  # (i, side) after cooldown + top filter, as the strategy does it
    for side, r in raw.items():
        last = -10**9
        for i in np.flatnonzero(r):
            if i - last < COOLDOWN_H or p not in top.get(months[i], set()):
                continue
            sigs.append((i, side))
            last = i
    out, busy = [], -1
    for i, side in sorted(sigs):
        if i <= busy or i + 1 >= len(c) or not (S <= idx[i] < E):
            continue
        e, k = c[i], STOP_K * sig24[i]
        stop = e * (1 - k) if side == 1 else e * (1 + k)
        res, j = None, i
        for j in range(i + 1, min(i + HOLD_H, len(c) - 1) + 1):
            if (side == 1 and l[j] <= stop) or (side == -1 and h[j] >= stop):
                res = (stop / e - 1) * side
                break
        if res is None:
            res = (c[j] / e - 1) * side
        out.append((p, "long" if side == 1 else "short", idx[i], idx[j], res - COST))
        busy = j
    return out


def main() -> None:
    OUT.mkdir(exist_ok=True)
    btc = pd.read_feather(bb.DATA / "BTC_USDT_USDT-1h-futures.feather").set_index("date").sort_index()
    bb.BTC_BEAR = (btc["close"] < btc["close"].rolling(1200).mean()).shift(1)
    bb.BTC_RET168 = btc["close"] / btc["close"].shift(168) - 1
    frames = load_all()
    top = top10_by_month(frames)
    print(f"{len(frames)} coins; top-10 sets for {len(top)} months; coins ever in top 10: {len(set().union(*top.values()))}", flush=True)

    rev, flow, closes = [], [], {}
    for n, (p, df) in enumerate(frames.items()):
        closes[p] = df["close"]
        sigs, _ = bb.signals(df)
        for k in ("rally_short", "flush_long"):
            side, sl, tp, hold = bb.IDEAS[k]
            rev += [(p, k, a, b, net) for a, b, net in bb.simulate(df, sigs[k].fillna(False).astype(bool), side, sl, tp, hold)]
        flow += f_trades(p, df, top)
        if n % 40 == 0:
            print(f"  {n}/{len(frames)} coins", flush=True)
    R = pd.DataFrame(rev, columns=["pair", "idea", "open", "close", "net"])
    F = pd.DataFrame(flow, columns=["pair", "side", "open", "close", "net"])
    F.to_csv(OUT / "trades_F.csv", index=False)

    # momentum basket weeks (unchanged from switcher.py)
    C = pd.DataFrame(closes)
    rows = []
    for t0 in C.index[(C.index.dayofweek == 0) & (C.index.hour == 0) & (C.index >= S) & (C.index < E)]:
        t1, tm = t0 + pd.Timedelta(hours=168), t0 - pd.Timedelta(days=30)
        if t1 not in C.index or tm not in C.index:
            continue
        mom = (C.loc[t0] / C.loc[tm] - 1).dropna()
        fwd = C.loc[t1] / C.loc[t0] - 1
        mom = mom[fwd.reindex(mom.index).notna()]
        if len(mom) < 40:
            continue
        lo, sh = fwd[mom.nlargest(10).index].mean() - COST, -fwd[mom.nsmallest(10).index].mean() - COST
        rows.append((t0.normalize(), (lo + sh) / 2))
    m_week = pd.Series(dict(rows))

    W = pd.DataFrame({"R": R.groupby(wk(R["open"]))["net"].mean(), "R_known": R.groupby(wk(R["close"]))["net"].mean(),
                      "F": F.groupby(wk(F["open"]))["net"].mean(), "F_known": F.groupby(wk(F["close"]))["net"].mean(),
                      "M": m_week, "F_n": F.groupby(wk(F["open"]))["net"].size()}).sort_index()
    W = W[W["M"].notna()].fillna({"R": 0.0, "R_known": 0.0, "F": 0.0, "F_known": 0.0, "F_n": 0})

    def switch(books: list[str], col: str) -> pd.Series:
        known = W[[b + "_known" if b != "M" else "M" for b in books]].rename(columns=lambda c_: c_.replace("_known", ""))
        trail = known.rolling(8).mean().shift(1)
        best = trail.fillna(-np.inf).idxmax(axis=1)  # first max wins: R before F before M
        pick = np.where((trail.max(axis=1) <= 0) | trail.isna().any(axis=1), "cash", best)
        W[col + "_pick"] = pick
        return pd.Series([W.loc[i, p] if p != "cash" else 0.0 for i, p in zip(W.index, pick)], index=W.index)

    W["sw2"] = switch(BOOKS2, "sw2")
    W["sw3"] = switch(BOOKS3, "sw3")
    W.to_csv(OUT / "weeks.csv")

    def judge(s: pd.Series, name: str) -> dict:
        eq = 300 * (1 + s).cumprod()
        dd = float((eq / eq.cummax() - 1).min() * 100)
        cum = s.cumsum(); under = cum < cum.cummax(); run = best = 0; end_i = None
        for i_, u in enumerate(under):
            run = run + 1 if u else 0
            if run > best:
                best, end_i = run, i_
        period = f"{s.index[end_i - best + 1].date()} .. {s.index[end_i].date()}" if end_i is not None and best else "-"
        mo = s.groupby(s.index.strftime("%Y-%m")).sum()
        yr = s.groupby(s.index.year).sum() * 100
        tot = float(s.sum() * 100)
        top3 = float(s.nlargest(3).sum() / s.sum() * 100) if tot > 0 else float("nan")
        d = {"weeks": int(len(s)), "sum_weekly_pct": round(tot, 1), "avg_week_pct": round(float(s.mean() * 100), 3),
             "per_year_avg_week_pct": {int(k): round(float(v), 2) for k, v in (s.groupby(s.index.year).mean() * 100).items()},
             "per_year_sum_pct": {int(k): round(float(v), 1) for k, v in yr.items()},
             "weeks_pos_pct": round(float((s > 0).mean() * 100), 1), "weeks_zero_pct": round(float((s == 0).mean() * 100), 1),
             "months_pos": f"{int((mo > 0).sum())}/{len(mo)}", "months_pos_pct": round(float((mo > 0).mean() * 100), 1),
             "years_pos": f"{int((yr > 0).sum())}/{len(yr)}", "top3_weeks_share_pct": None if np.isnan(top3) else round(top3, 1),
             "longest_under_high_weeks": int(best), "longest_under_high_period": period,
             "top3_weeks": [(str(k.date()), round(float(v) * 100, 2)) for k, v in s.nlargest(3).items()],
             "worst_week_pct": round(float(s.min() * 100), 2),
             "book300_final": round(float(eq.iloc[-1]), 1), "book300_worst_drop_pct": round(dd, 1)}
        rule = (d["months_pos_pct"] >= 60 and (yr > 0).all() and (top3 == top3 and top3 <= 25) and best <= 16)
        d["consistency_rule"] = "pass" if rule else "fail"
        return d

    res = {b: judge(W[b], b) for b in ("R", "F", "M")}
    res["switcher_RM"] = judge(W["sw2"], "sw2")
    res["switcher_RFM"] = judge(W["sw3"], "sw3")
    for col, key in (("sw2_pick", "switcher_RM"), ("sw3_pick", "switcher_RFM")):
        res[key]["picked"] = W[col].value_counts().to_dict()
    span_w = (F["open"].max() - F["open"].min()).days / 7
    res["F"]["trades"] = int(len(F)); res["F"]["trades_per_week"] = round(len(F) / span_w, 2)
    res["F"]["weeks_with_trade_pct"] = round(float((W["F_n"] > 0).mean() * 100), 1)
    res["F"]["avg_trade_pct"] = round(float(F["net"].mean() * 100), 3); res["F"]["win_pct"] = round(float((F["net"] > 0).mean() * 100), 1)
    res["F"]["long_short"] = F["side"].value_counts().to_dict()
    a, b_ = res["switcher_RFM"], res["switcher_RM"]
    ok = a["consistency_rule"] == "pass" and a["sum_weekly_pct"] > b_["sum_weekly_pct"] and a["longest_under_high_weeks"] < b_["longest_under_high_weeks"]
    res["verdict"] = "🟡 paper forward test" if ok else "🔴"
    res["check_vs_1024_run"] = {"sw2_sum_here": res["switcher_RM"]["sum_weekly_pct"], "sw_sum_1024": 194.1}
    (OUT / "result.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")

    md = ["# Switcher-3 result (automatic, rule unchanged; re-run 2026-11-12 00:30 after fixing the 'best 3 weeks share' column, "
          "which printed a ratio instead of a percent - numbers otherwise identical)", "",
          "| book | sum weekly % | avg/week | weeks + | months + | years + | best 3 weeks share | longest under high | 300 USDT book | worst drop | rule |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in ("R", "F", "M", "switcher_RM", "switcher_RFM"):
        d = res[k]
        md.append(f"| {k} | {d['sum_weekly_pct']:+.1f} | {d['avg_week_pct']:+.3f}% | {d['weeks_pos_pct']}% | {d['months_pos']} | {d['years_pos']} | "
                  f"{d['top3_weeks_share_pct']}% | {d['longest_under_high_weeks']} wk ({d['longest_under_high_period']}) | {d['book300_final']} | {d['book300_worst_drop_pct']}% | {d['consistency_rule']} |")
    f = res["F"]
    md += ["", f"F alone: {f['trades']} trades = {f['trades_per_week']}/week, a trade in {f['weeks_with_trade_pct']}% of weeks, avg {f['avg_trade_pct']:+.3f}%/trade, win {f['win_pct']}%, {f['long_short']}.",
           f"Per-year sum % - R {res['R']['per_year_sum_pct']} | F {f['per_year_sum_pct']} | M {res['M']['per_year_sum_pct']} | "
           f"Switcher R/M {res['switcher_RM']['per_year_sum_pct']} | Switcher R/F/M {res['switcher_RFM']['per_year_sum_pct']}",
           f"Picked: R/M {res['switcher_RM']['picked']} | R/F/M {res['switcher_RFM']['picked']}",
           f"Check: Switcher R/M sum here {res['check_vs_1024_run']['sw2_sum_here']} vs 194.1 in the 10-24 re-run.",
           f"Best 3 weeks: R/M {res['switcher_RM']['top3_weeks']} | R/F/M {res['switcher_RFM']['top3_weeks']}",
           f"", f"**Verdict: {res['verdict']}**"]
    text = "\n".join(md) + "\n"
    (OUT / "REPORT.md").write_text(text, encoding="utf-8")
    (HERE / "REGISTER_SWITCHER3_2026-11-12.md").open("a", encoding="utf-8").write("\n" + text.replace("# Switcher-3 result", "## Result"))
    print(text, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
