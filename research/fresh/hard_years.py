"""Search from the hard years (2026-11-12): weekly market-neutral baskets, settings chosen on 2022-02..2023-12 only.
Rule: REGISTER_HARD_YEARS_2026-11-12.md.

    .venv\\Scripts\\python.exe research\\fresh\\hard_years.py

Output: research/fresh/hard_years/{weeks_<family>_<setting>.csv, result.json, REPORT.md}; result appended to the register.
Report-only. Nothing trades.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bear_batch as bb  # noqa: E402

OUT = HERE / "hard_years"
S, E = pd.Timestamp("2022-02-07", tz="UTC"), pd.Timestamp("2026-10-01", tz="UTC")
CHOOSE_END = pd.Timestamp("2024-01-01", tz="UTC")
COST, N, MIN_COINS, WALLET = bb.COST, 10, 40, 300.0
FAMILIES = {"A reversal": [3, 7, 14], "B momentum": [30, 60, 90], "C volatility": [14, 30, 60], "D funding": [3, 7, 14], "E attention": [7]}


def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    closes, vols, funds = {}, {}, {}
    for p in bb.PAIRS:
        c = p.split("/")[0]
        f = bb.DATA / f"{c}_USDT_USDT-1h-futures.feather"
        if not f.exists():
            continue
        df = pd.read_feather(f).set_index("date").sort_index()
        if len(df) < 500:
            continue
        closes[p], vols[p] = df["close"], df["close"] * df["volume"]
        ff = bb.DATA / f"{c}_USDT_USDT-1h-funding_rate.feather"
        if ff.exists():
            funds[p] = pd.read_feather(ff).drop_duplicates("date").set_index("date").sort_index()["funding_rate"]
    return pd.DataFrame(closes), pd.DataFrame(vols), pd.DataFrame(funds)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    C, QV, FU = load()
    D = C[C.index.hour == 0]                                  # daily closes (00:00 UTC candle open price = close of 23:00 candle)
    dret = D.pct_change()
    mondays = C.index[(C.index.dayofweek == 0) & (C.index.hour == 0) & (C.index >= S) & (C.index < E)]
    FU = FU.sort_index()
    print(f"{C.shape[1]} coins, {FU.shape[1]} with funding, {len(mondays)} Mondays", flush=True)

    def signal(fam: str, k: int, t0: pd.Timestamp) -> pd.Series | None:
        """Higher = better for the LONG side. Only data up to t0."""
        if fam == "A reversal":
            tm = t0 - pd.Timedelta(days=k)
            return -(C.loc[t0] / C.loc[tm] - 1) if tm in C.index else None
        if fam == "B momentum":
            tm = t0 - pd.Timedelta(days=k)
            return (C.loc[t0] / C.loc[tm] - 1) if tm in C.index else None
        if fam == "C volatility":
            w = dret[dret.index <= t0].tail(k)
            if len(w) < k:
                return None
            sd = w.std(); sd = sd[w.notna().sum() >= int(k * 0.8)]
            return -sd
        if fam == "D funding":
            w = FU[(FU.index > t0 - pd.Timedelta(days=k)) & (FU.index <= t0)]
            if not len(w):
                return None
            m = w.mean(); m = m[w.notna().sum() >= 3 * k * 0.8]
            return -m
        if fam == "E attention":
            a = QV[(QV.index > t0 - pd.Timedelta(days=7)) & (QV.index <= t0)].sum()
            b = QV[(QV.index > t0 - pd.Timedelta(days=90)) & (QV.index <= t0)]
            ok = b.notna().sum() >= 24 * 60
            ratio = a / (b.sum() / 90 * 7).replace(0, np.nan)
            return -ratio[ok]
        return None

    rows_all = {}
    for fam, ks in FAMILIES.items():
        for k in ks:
            rows = []
            for t0 in mondays:
                t1 = t0 + pd.Timedelta(hours=168)
                if t1 not in C.index:
                    continue
                sig = signal(fam, k, t0)
                if sig is None:
                    continue
                fwd = C.loc[t1] / C.loc[t0] - 1
                sig = sig.dropna(); sig = sig[fwd.reindex(sig.index).notna()]
                if len(sig) < MIN_COINS:
                    rows.append({"week": t0.normalize(), "price": 0.0, "fund": 0.0, "n": len(sig)})
                    continue
                lo, sh = sig.nlargest(N).index, sig.nsmallest(N).index
                price = (fwd[lo].mean() - fwd[sh].mean()) / 2 - COST
                fw = FU[(FU.index > t0) & (FU.index <= t1)].sum()
                fund = (-fw.reindex(lo).fillna(0).mean() + fw.reindex(sh).fillna(0).mean()) / 2
                rows.append({"week": t0.normalize(), "price": price, "fund": fund, "n": len(sig)})
            w = pd.DataFrame(rows).set_index("week")
            w["total"] = w["price"] + w["fund"]
            w.to_csv(OUT / f"weeks_{fam.split()[0]}_{k}.csv")
            rows_all[(fam, k)] = w
        print(f"  {fam} done", flush=True)

    def judge(s: pd.Series) -> dict:
        eq = WALLET * (1 + s).cumprod()
        dd = float((eq / eq.cummax() - 1).min() * 100)
        cum = s.cumsum(); under = cum < cum.cummax(); run = best = 0; end_i = None
        for i_, u in enumerate(under):
            run = run + 1 if u else 0
            if run > best:
                best, end_i = run, i_
        period = f"{s.index[end_i - best + 1].date()} .. {s.index[end_i].date()}" if best else "-"
        mo = s.groupby(s.index.strftime("%Y-%m")).sum()
        yr = s.groupby(s.index.year).sum() * 100
        tot = float(s.sum() * 100)
        top3 = float(s.nlargest(3).sum() / s.sum() * 100) if tot > 0 else float("nan")
        d = {"weeks": int(len(s)), "sum_weekly_pct": round(tot, 1), "avg_week_pct": round(float(s.mean() * 100), 3),
             "per_year_sum_pct": {int(k): round(float(v), 1) for k, v in yr.items()},
             "weeks_pos_pct": round(float((s > 0).mean() * 100), 1), "months_pos": f"{int((mo > 0).sum())}/{len(mo)}",
             "months_pos_pct": round(float((mo > 0).mean() * 100), 1), "years_pos": f"{int((yr > 0).sum())}/{len(yr)}",
             "top3_weeks_share_pct": None if np.isnan(top3) else round(top3, 1),
             "top3_weeks": [(str(k.date()), round(float(v) * 100, 2)) for k, v in s.nlargest(3).items()],
             "longest_under_high_weeks": int(best), "longest_under_high_period": period, "worst_week_pct": round(float(s.min() * 100), 2),
             "weekly_sd_pct": round(float(s.std() * 100), 2), "book300_final": round(float(eq.iloc[-1]), 1), "book300_worst_drop_pct": round(dd, 1)}
        d["consistency_rule"] = "pass" if (d["months_pos_pct"] >= 60 and (yr > 0).all() and top3 == top3 and top3 <= 25 and best <= 16) else "fail"
        return d

    def half(s: pd.Series, a, b) -> dict:
        x = s[(s.index >= a) & (s.index < b)]
        mo = x.groupby(x.index.strftime("%Y-%m")).sum()
        return {"months_pos": f"{int((mo > 0).sum())}/{len(mo)}", "months_pos_n": int((mo > 0).sum()), "sum_pct": round(float(x.sum() * 100), 1),
                "weeks_pos_pct": round(float((x > 0).mean() * 100), 1)}

    # menu table + choice on 2022-23 only
    menu, chosen = [], {}
    for (fam, k), w in rows_all.items():
        s = w["total"]
        h1, h2 = half(s, S, CHOOSE_END), half(s, CHOOSE_END, E)
        menu.append({"family": fam, "k": k, "2022_23": h1, "2024_26": h2, "avg_coins": round(float(w["n"].mean()), 1)})
    for fam in FAMILIES:
        cand = [m for m in menu if m["family"] == fam]
        best = sorted(cand, key=lambda m: (m["2022_23"]["months_pos_n"], m["2022_23"]["sum_pct"]), reverse=True)[0]
        chosen[fam] = best["k"]
    res = {"menu": menu, "chosen": chosen, "final": {}}
    series = {}
    for fam, k in chosen.items():
        w = rows_all[(fam, k)]
        series[fam] = w["total"]
        d = judge(w["total"]); d["price_only"] = judge(w["price"]); d["funding_part_sum_pct"] = round(float(w["fund"].sum() * 100), 1)
        d["avg_coins_ranked"] = round(float(w["n"].mean()), 1); d["2024_26_sum_pct"] = half(w["total"], CHOOSE_END, E)["sum_pct"]
        d["verdict"] = "🟡 paper forward test" if d["consistency_rule"] == "pass" and d["2024_26_sum_pct"] > 0 else "🔴"
        res["final"][f"{fam} k={k}"] = d
    mix = pd.concat(series, axis=1).fillna(0).mean(axis=1)
    d = judge(mix); d["2024_26_sum_pct"] = half(mix, CHOOSE_END, E)["sum_pct"]
    d["verdict"] = "🟡 paper forward test" if d["consistency_rule"] == "pass" and d["2024_26_sum_pct"] > 0 else "🔴"
    res["final"]["MIX of the five"] = d
    pd.concat(series, axis=1).assign(MIX=mix).to_csv(OUT / "weeks_chosen.csv")
    (OUT / "result.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")

    md = ["# Hard-years search result (automatic, rule unchanged)", "", "## Menu (choice made on the 2022-23 columns only)", "",
          "| family | k | 2022-23 months + | 2022-23 sum % | 2024-26 months + | 2024-26 sum % | coins ranked | chosen |", "|---|---|---|---|---|---|---|---|"]
    for m in menu:
        md.append(f"| {m['family']} | {m['k']} | {m['2022_23']['months_pos']} | {m['2022_23']['sum_pct']:+.1f} | {m['2024_26']['months_pos']} | "
                  f"{m['2024_26']['sum_pct']:+.1f} | {m['avg_coins']} | {'yes' if chosen[m['family']] == m['k'] else ''} |")
    md += ["", "## Chosen settings on the full period 2022-02 .. 2026-09 (with funding)", "",
           "| setting | sum weekly % | avg/week | weeks + | months + | years + | best 3 weeks | longest under high | 300 USDT book | worst drop | price-only sum | verdict |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, d in res["final"].items():
        po = d.get("price_only", {}).get("sum_weekly_pct", "-")
        md.append(f"| {k} | {d['sum_weekly_pct']:+.1f} | {d['avg_week_pct']:+.3f}% | {d['weeks_pos_pct']}% | {d['months_pos']} | {d['years_pos']} | "
                  f"{d['top3_weeks_share_pct']}% | {d['longest_under_high_weeks']} wk ({d['longest_under_high_period']}) | {d['book300_final']} | "
                  f"{d['book300_worst_drop_pct']}% | {po} | {d['verdict']} |")
    md += ["", "Per-year sum %: " + " | ".join(f"{k}: {d['per_year_sum_pct']}" for k, d in res["final"].items()),
           "Best 3 weeks: " + " | ".join(f"{k}: {d['top3_weeks']}" for k, d in res["final"].items()), ""]
    text = "\n".join(md) + "\n"
    (OUT / "REPORT.md").write_text(text, encoding="utf-8")
    (HERE / "REGISTER_HARD_YEARS_2026-11-12.md").open("a", encoding="utf-8").write("\n" + text.replace("# Hard-years search result", "## Result"))
    print(text, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
