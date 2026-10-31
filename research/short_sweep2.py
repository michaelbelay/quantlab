"""Second short-side sweep: the parameter and exit-geometry search the first pass never got.

Gates are pre-registered in PREREGISTRATION_2026-09-24_shortsweep.md and are
encoded here, not restated loosely, so the verdict cannot drift to fit results.

Stage 1 screens on the 70 dev coins. Only what clears stage 1 is allowed near the
holdout, which keeps the unseen set unseen for as long as possible.

Resumable: every combination appends to short_sweep2.jsonl as it finishes, so a
killed run continues instead of restarting. This host has killed long runs before.

    python research/short_sweep2.py                 # stage 1, dev coins
    python research/short_sweep2.py --report        # rank what is already done
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "engine"))
import backtest as bt                              # noqa: E402
from backtest import Config, simulate_pair         # noqa: E402
from features import load_pair                     # noqa: E402

LEDGER = HERE / "short_sweep2.jsonl"
UNI = ROOT / "data" / "market" / "universe"
WALLET = 1000.0

# Each family's own parameter, swept around its default.
FAMILY_PARAMS = {
    "breakdown":               [{"close_pos_max": v} for v in (0.25, 0.35, 0.45)],
    "resistance_rejection":    [{"tol_atr": t, "wick_min": w}
                                for t in (0.35, 0.6) for w in (0.3, 0.4, 0.5)],
    "breakdown_retest":        [{"retest_win": v} for v in (8, 12, 20)],
    "vwap_rejection":          [{"near_atr": n, "win": w}
                                for n in (0.5, 0.8) for w in (6, 12)],
    "lower_high":              [{"swing_win": v} for v in (6, 10, 16)],
    "bear_trend_continuation": [{"adx_max": a, "bounce_win": b}
                                for a in (35, 45, 55) for b in (3, 5, 8)],
    "bear_divergence":         [{}],
    "volume_breakdown":        [{"vol_mult": v} for v in (1.2, 1.5, 2.0)],
    "downside_vol_expansion":  [{"expand_min": v} for v in (1.15, 1.3, 1.6)],
}
STOPS = (2.0, 3.0, 4.0)
MAXBARS = (200, 400, 800)
FILTERS = {"nofilt": [], "btc": ["btc_regime"], "btc+vol": ["btc_regime", "volume"]}

REGIMES = [("bull2021", "2021-01-01", "2021-11-10"),
           ("bear2022", "2021-11-10", "2023-01-01"),
           ("recovery2023_24", "2023-01-01", "2025-01-01"),
           ("recent2025_26", "2025-01-01", "2026-10-01")]

# Stage-1 gate, exactly as pre-registered.
MIN_TRADES_PER_YEAR = 100
MIN_PF = 1.10
MIN_PF_2X = 1.05


def ts(x):
    return pd.Timestamp(x, tz="UTC")


def load_dev():
    split = json.loads((UNI / "split_140.json").read_text(encoding="utf-8"))
    uni = {}
    for c in split["dev"]:
        f = load_pair(c, futures=True)
        if f is not None and len(f.close) >= 400:
            uni[c] = f
    return uni


def done_keys() -> set:
    if not LEDGER.exists():
        return set()
    out = set()
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        try:
            out.add(json.loads(line)["cid"])
        except Exception:
            pass
    return out


def run(uni, spec, cfg, fee_mult=1.0):
    of, os_ = bt.FEE, bt.SLIP
    bt.FEE, bt.SLIP = of * fee_mult, os_ * fee_mult
    try:
        rows = []
        for pair, f in uni.items():
            for t in simulate_pair(f, spec, cfg, pair):
                rows.append({"pair": pair, "pnl": t.pnl,
                             "entry": pd.Timestamp(f.date[t.entry_i])})
        df = pd.DataFrame(rows)
        if not df.empty:
            df["entry"] = pd.to_datetime(df.entry, utc=True)
        return df
    finally:
        bt.FEE, bt.SLIP = of, os_


def pf_of(df):
    if df.empty:
        return None
    w = df[df.pnl > 0].pnl.sum()
    l = -df[df.pnl < 0].pnl.sum()
    return round(w / l, 4) if l > 0 else None


def report():
    rows = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = [r for r in rows if r.get("stage1_pass")]
    rows.sort(key=lambda r: -(r.get("pf_2x") or 0))
    print(f"{len(rows)} combinations run, {len(ok)} cleared stage 1\n")
    print(f"{'combination':<58}{'tr/yr':>7}{'PF':>8}{'PF 2x':>8}{'bear22':>9}{'recent':>9}{'pass':>6}")
    for r in rows[:30]:
        print(f"{r['cid']:<58}{r.get('per_year') or 0:>7.0f}{r.get('pf') or 0:>8.3f}"
              f"{r.get('pf_2x') or 0:>8.3f}{r.get('bear2022') or 0:>9.1f}"
              f"{r.get('recent2025_26') or 0:>9.1f}{'YES' if r.get('stage1_pass') else '':>6}")
    if not ok:
        best = max((r.get("pf_2x") or 0) for r in rows) if rows else 0
        print(f"\nNothing cleared stage 1. Best 2x-cost PF was {best:.3f} "
              f"against the pre-registered floor of {MIN_PF_2X}.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        report()
        return 0

    uni = load_dev()
    print(f"dev coins: {len(uni)}", flush=True)
    combos = []
    for fam, plist in FAMILY_PARAMS.items():
        for params, stop, mb, (fname, filts) in itertools.product(
                plist, STOPS, MAXBARS, FILTERS.items()):
            ptag = ",".join(f"{k}={v}" for k, v in params.items()) or "default"
            combos.append((f"{fam}|{ptag}|stop{stop}|bars{mb}|{fname}",
                           fam, params, stop, mb, filts))
    seen = done_keys()
    todo = [c for c in combos if c[0] not in seen]
    print(f"{len(combos)} combinations, {len(seen)} already done, {len(todo)} to run\n", flush=True)

    t0 = time.time()
    for i, (cid, fam, params, stop, mb, filts) in enumerate(todo, 1):
        cfg = Config(leverage=1.0, stop_mode="atr", stop_atr=stop, tp_mode="none",
                     tp_atr=(), tp_frac=(), entry_mode="instant", max_bars=mb)
        spec = {"family": fam, "direction": "short", "filters": filts,
                "trend_mode": "with", "params": params}
        df = run(uni, spec, cfg)
        rec = {"cid": cid, "family": fam, "params": params, "stop_atr": stop,
               "max_bars": mb, "filters": ",".join(filts) or "nofilt"}
        if df.empty or len(df) < 50:
            rec.update(trades=int(len(df)), stage1_pass=False, reason="too few trades")
        else:
            yrs = (df.entry.max() - df.entry.min()).days / 365.25
            df2 = run(uni, spec, cfg, fee_mult=2.0)
            pf, pf2 = pf_of(df), pf_of(df2)
            per_year = len(df) / yrs
            regs = {n: round(df[(df.entry >= ts(s)) & (df.entry < ts(e))].pnl.sum() / WALLET * 100, 1)
                    for n, s, e in REGIMES}
            rec.update(trades=int(len(df)), per_year=round(per_year, 1),
                       ret_pct=round(df.pnl.sum() / WALLET * 100, 1),
                       pf=pf, pf_2x=pf2, **regs)
            rec["stage1_pass"] = bool(
                per_year >= MIN_TRADES_PER_YEAR and pf and pf >= MIN_PF
                and pf2 and pf2 >= MIN_PF_2X
                and regs["bear2022"] > 0 and regs["recent2025_26"] > 0)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        if i % 10 == 0 or rec.get("stage1_pass"):
            el = time.time() - t0
            print(f"[{i}/{len(todo)}] {el/60:.1f}m  {cid[:52]:<52} "
                  f"PF {rec.get('pf') or 0:.3f} / 2x {rec.get('pf_2x') or 0:.3f}"
                  f"{'   <-- STAGE 1 PASS' if rec.get('stage1_pass') else ''}", flush=True)

    print("\nSWEEP COMPLETE")
    report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
