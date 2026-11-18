"""Weekly basket with sizing variants B0..B3 (2026-11-12). Rule: REGISTER_BASKET_SIZING_2026-11-12.md.

    .venv\\Scripts\\python.exe research\\fresh\\basket_sizing.py

Output: research/fresh/basket_sizing/{weeks.csv, result.json, REPORT.md}; result appended to the register. Report-only.
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

OUT = HERE / "basket_sizing"
S, E = pd.Timestamp("2022-02-07", tz="UTC"), pd.Timestamp("2026-10-01", tz="UTC")
COST, N, TARGET, SD_W, SD_MIN, E_EARLY, WALLET = bb.COST, 10, 0.03, 13, 8, 0.5, 300.0


def load_closes() -> pd.DataFrame:
    closes = {}
    for p in bb.PAIRS:
        f = bb.DATA / f"{p.split('/')[0]}_USDT_USDT-1h-futures.feather"
        if f.exists():
            df = pd.read_feather(f).set_index("date").sort_index()
            if len(df) >= 500:
                closes[p] = df["close"]
    return pd.DataFrame(closes)


def weeks(C: pd.DataFrame) -> pd.DataFrame:
    """Per Monday: unscaled weekly result for equal weights (ew) and inverse-vol weights (iv), plus leg sizes."""
    D = C[C.index.hour == 0]
    sd30 = D.pct_change().rolling(30, min_periods=20).std()
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
        top, bot = mom.nlargest(N).index, mom.nsmallest(N).index
        ew = (fwd[top].mean() - fwd[bot].mean()) / 2 - COST
        legs = {}
        for names, sign in ((top, 1), (bot, -1)):
            s = sd30.loc[t0, names] if t0 in sd30.index else pd.Series(np.nan, index=names)
            s = s.fillna(s.median()) if s.notna().any() else pd.Series(1.0, index=names)
            w = (1 / s) / (1 / s).sum() * 0.5
            legs[sign] = w
        iv = float((legs[1] * fwd[top]).sum() - (legs[-1] * fwd[bot]).sum()) - COST
        allw = pd.concat([legs[1], legs[-1]])
        rows.append({"week": t0.normalize(), "ew": ew, "iv": iv, "leg_min": float(allw.min()), "leg_med": float(allw.median())})
    return pd.DataFrame(rows).set_index("week")


def exposure(unscaled: pd.Series) -> pd.Series:
    sd = unscaled.rolling(SD_W, min_periods=SD_MIN).std().shift(1)
    e = (TARGET / sd).clip(upper=1.0)
    return e.fillna(E_EARLY)


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
         "per_year_avg_week_pct": {int(k): round(float(v), 2) for k, v in (s.groupby(s.index.year).mean() * 100).items()},
         "per_year_sum_pct": {int(k): round(float(v), 1) for k, v in yr.items()},
         "weeks_pos_pct": round(float((s > 0).mean() * 100), 1), "months_pos": f"{int((mo > 0).sum())}/{len(mo)}",
         "months_pos_pct": round(float((mo > 0).mean() * 100), 1), "years_pos": f"{int((yr > 0).sum())}/{len(yr)}",
         "top3_weeks_share_pct": None if np.isnan(top3) else round(top3, 1),
         "top3_weeks": [(str(k.date()), round(float(v) * 100, 2)) for k, v in s.nlargest(3).items()],
         "longest_under_high_weeks": int(best), "longest_under_high_period": period, "worst_week_pct": round(float(s.min() * 100), 2),
         "weekly_sd_pct": round(float(s.std() * 100), 2), "book300_final": round(float(eq.iloc[-1]), 1), "book300_worst_drop_pct": round(dd, 1)}
    d["consistency_rule"] = "pass" if (d["months_pos_pct"] >= 60 and (yr > 0).all() and top3 == top3 and top3 <= 25 and best <= 16) else "fail"
    return d


def main() -> None:
    OUT.mkdir(exist_ok=True)
    C = load_closes()
    W = weeks(C)
    print(f"{C.shape[1]} coins, {len(W)} weeks", flush=True)
    e1, e3 = exposure(W["ew"]), exposure(W["iv"])
    V = {"B0 equal weight, full": W["ew"], "B1 vol target 3%": W["ew"] * e1, "B2 inverse-vol legs": W["iv"], "B3 inverse-vol + vol target": W["iv"] * e3}
    X = {"B0 equal weight, full": 1.0, "B1 vol target 3%": e1, "B2 inverse-vol legs": 1.0, "B3 inverse-vol + vol target": e3}
    W["B1_e"], W["B3_e"] = e1, e3
    W.to_csv(OUT / "weeks.csv")
    res = {}
    for k, s in V.items():
        d = judge(s)
        d["avg_exposure_pct"] = round(float(np.mean(X[k]) * 100), 1) if not isinstance(X[k], float) else 100.0
        if "inverse" in k:
            ex = X[k] if not isinstance(X[k], float) else 1.0
            d["leg_min_usdt_at_300"] = round(float((W["leg_min"] * ex * WALLET).min()), 2)
            d["leg_med_usdt_at_300"] = round(float((W["leg_med"] * ex * WALLET).median()), 2)
        res[k] = d
    res["verdict"] = {k: ("🟡 paper forward test" if v["consistency_rule"] == "pass" else "🔴") for k, v in res.items()}
    (OUT / "result.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    md = ["# Basket sizing result (automatic, rule unchanged)", "",
          "| variant | sum weekly % | avg/week | weekly sd | weeks + | months + | years + | best 3 weeks | longest under high | 300 USDT book | worst drop | avg exposure | rule |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, d in res.items():
        if k == "verdict":
            continue
        md.append(f"| {k} | {d['sum_weekly_pct']:+.1f} | {d['avg_week_pct']:+.3f}% | {d['weekly_sd_pct']}% | {d['weeks_pos_pct']}% | {d['months_pos']} | {d['years_pos']} | "
                  f"{d['top3_weeks_share_pct']}% | {d['longest_under_high_weeks']} wk ({d['longest_under_high_period']}) | {d['book300_final']} | "
                  f"{d['book300_worst_drop_pct']}% | {d['avg_exposure_pct']}% | {d['consistency_rule']} |")
    md += ["", "Per-year sum %: " + " | ".join(f"{k}: {d['per_year_sum_pct']}" for k, d in res.items() if k != "verdict"),
           "Best 3 weeks: " + " | ".join(f"{k}: {d['top3_weeks']}" for k, d in res.items() if k != "verdict"),
           "Leg sizes at 300 USDT (inverse-vol): " + " | ".join(f"{k}: min {d['leg_min_usdt_at_300']}, median {d['leg_med_usdt_at_300']}" for k, d in res.items() if k != "verdict" and "inverse" in k),
           "", f"**Verdict: {res['verdict']}**"]
    text = "\n".join(md) + "\n"
    (OUT / "REPORT.md").write_text(text, encoding="utf-8")
    (HERE / "REGISTER_BASKET_SIZING_2026-11-12.md").open("a", encoding="utf-8").write("\n" + text.replace("# Basket sizing result", "## Result"))
    print(text, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
