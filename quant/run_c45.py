r"""C45 Power of 3 - London sweep fade (FAMILIES_C.md "C45", registered 2026-10-18 before this file existed).

    .venv\Scripts\python.exe -m quant.run_c45 dev      # generate trades (all periods) + judge DEV only
    .venv\Scripts\python.exe -m quant.run_c45 valid    # refused without a recorded DEV pass
    .venv\Scripts\python.exe -m quant.run_c45 wf       # refused without a recorded VALID pass

Asia range 00-07 UTC; London (07-10) sweeps exactly one side and the 09:00 bar closes back inside; trade against the
sweep at the 10:00 open; stop = sweep extreme, target = other side of the Asia range, time exit 20:00 UTC.
Universe = the 46 live-bot coins. Trades -> runs/c_trades/C45/1h/<coin>.parquet; results -> runs/ledger_c.jsonl.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import trades as T
from .bars import bars
from .eval_c import PERIODS, WALK_FORWARD, ledger, mins
from .paths import RUNS
from .run_c42_c43 import REPS, coins, evaluate, period_gate

OUT = RUNS / "c_trades" / "C45" / "1h"
DEV = ("2021-01-01", "2024-07-01")


def day_grid(df: pd.DataFrame) -> tuple[np.ndarray, pd.DatetimeIndex]:
    """pos[d, h] = row index of the bar opening at hour h of day d (-1 when missing)."""
    day = df["date"].dt.floor("D")
    days = pd.DatetimeIndex(day.unique())
    di = days.get_indexer(day)
    pos = np.full((len(days), 24), -1, dtype=np.int64)
    pos[di, df["date"].dt.hour.to_numpy()] = np.arange(len(df))
    return pos, days


def c45_trades(df: pd.DataFrame, cost_mult: float = 1.0) -> list[dict]:
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    fund, dates = df["fund"].to_numpy(), df["date"].to_numpy()
    ok = T.eligible(df, 24)
    pos, _ = day_grid(df)
    cost, sx = (T.FEE + T.SLIP) * cost_mult, T.STOP_EXTRA * cost_mult
    out = []
    for p in pos:
        if (p[:20] < 0).any():                       # need every bar 00:00 .. 19:00
            continue
        asia_hi, asia_lo = h[p[0:7]].max(), l[p[0:7]].min()
        lon = p[7:10]
        up, dn = (h[lon] > asia_hi).any(), (l[lon] < asia_lo).any()
        if up == dn:                                 # no sweep, or both sides swept
            continue
        if not (asia_lo < c[p[9]] < asia_hi):        # London must close back inside the range
            continue
        e = p[10]
        if not ok[e]:
            continue
        side = -1 if up else 1
        stop = h[lon].max() if up else l[lon].min()
        tp = asia_lo if up else asia_hi
        px = o[e]
        if (side == -1 and (px >= stop or px <= tp)) or (side == 1 and (px <= stop or px >= tp)):
            continue
        x, reason, xp = p[19], "time", c[p[19]]
        for j in p[10:20]:
            hit_stop = h[j] >= stop if side == -1 else l[j] <= stop
            hit_tp = l[j] <= tp if side == -1 else h[j] >= tp
            if hit_stop:
                gap = o[j] > stop if side == -1 else o[j] < stop
                xp = (o[j] if gap else stop) * (1 - side * sx)
                x, reason = j, "stop"
                break
            if hit_tp:
                x, reason, xp = j, "tp", tp
                break
        gross = side * (xp / px - 1)
        f = side * fund[e:x + 1].sum()
        mae = (l[e:x + 1].min() / px - 1) if side == 1 else -(h[e:x + 1].max() / px - 1)
        out.append({"side": side, "entry_i": e, "exit_i": x, "entry_t": dates[e], "exit_t": dates[x],
                    "ret": gross - 2 * cost - f,                      # stop extra slippage is already in xp
                    "gross": gross, "funding": f, "mae": mae, "reason": reason, "bars": x - e + 1,
                    "cost": 2 * cost + (sx if reason == "stop" else 0.0)})
    return out


def twins(df: pd.DataFrame, tr: list[dict], rng) -> np.ndarray:
    """Same coin, side, holding and cost; entered at the 10:00 UTC open of a random DEV day."""
    if not tr:
        return np.zeros(REPS)
    o, c = df["open"].to_numpy(), df["close"].to_numpy()
    pos, days = day_grid(df)
    m = (days >= pd.Timestamp(DEV[0], tz="UTC")) & (days < pd.Timestamp(DEV[1], tz="UTC")) & (pos[:, 10] >= 0)
    pool = pos[m, 10]
    side = np.array([t["side"] for t in tr])
    b = np.array([t["bars"] for t in tr])
    cost = np.array([t["cost"] for t in tr])
    pool = pool[pool + b.max() < len(c)]
    out = np.zeros(REPS)
    for r in range(REPS):
        e = pool[(rng.random(len(b)) * len(pool)).astype(int)]
        out[r] = np.nansum(side * (c[e + b - 1] / o[e] - 1) - cost)
    return out


def generate() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for i, coin in enumerate(coins()):
        f_out = OUT / f"{coin}.parquet"
        if f_out.exists():
            continue
        df = bars(coin, "1h")
        tr = c45_trades(df)
        x2 = {t["entry_i"]: t for t in c45_trades(df, 2.0)}
        for t in tr:
            t["ret_x2"] = x2[t["entry_i"]]["ret"]
            t["family"], t["coin"] = "C45", coin
        dev = [t for t in tr if pd.Timestamp(t["entry_t"]).tz_localize("UTC") < pd.Timestamp(DEV[1], tz="UTC")] \
            if tr and pd.Timestamp(tr[0]["entry_t"]).tzinfo is None else \
            [t for t in tr if pd.Timestamp(t["entry_t"]) < pd.Timestamp(DEV[1], tz="UTC")]
        tw = twins(df, dev, np.random.default_rng([i, 45]))
        res = pd.DataFrame(tr)
        if len(res):
            res = res.drop(columns=["entry_i", "exit_i"])
        res.to_parquet(f_out)
        np.savez(OUT / f"{coin}.twins.npz", C45=tw)
        print(f"  C45 {coin}: {len(tr)} trades", flush=True)


def load(a: str, b: str) -> tuple[pd.DataFrame, np.ndarray]:
    parts, tw = [], np.zeros(REPS)
    lo, hi = pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC")
    for f in sorted(OUT.glob("*.parquet")):
        x = pd.read_parquet(f)
        if len(x):
            for col in ("entry_t", "exit_t"):
                x[col] = pd.to_datetime(x[col], utc=True)
            parts.append(x[(x["entry_t"] >= lo) & (x["entry_t"] < hi)])
        z = OUT / f"{f.stem}.twins.npz"
        if z.exists():
            tw = tw + np.load(z)["C45"]
    return pd.concat(parts, ignore_index=True), tw


def extras(t: pd.DataFrame) -> dict:
    wk = t["entry_t"].dt.weekday >= 5
    pf = lambda x: round(float(x[x > 0].sum() / max(1e-9, -x[x < 0].sum())), 3)
    return {"weekday": {"trades": int((~wk).sum()), "pf": pf(t.loc[~wk, "ret"])},
            "weekend": {"trades": int(wk.sum()), "pf": pf(t.loc[wk, "ret"])},
            "long_all": {"trades": int((t.side == 1).sum()), "pf": pf(t.loc[t.side == 1, "ret"])},
            "short_all": {"trades": int((t.side == -1).sum()), "pf": pf(t.loc[t.side == -1, "ret"])}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["dev", "valid", "wf"])
    a = ap.parse_args()
    mn = mins()
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = [json.loads(l) for l in open(RUNS / "ledger_c.jsonl", encoding="utf-8")]
    has = lambda stage, v: any(r["family"] == "C45" and r["stage"] == stage and r["verdict"] == v for r in rows)
    if a.stage == "dev":
        generate()
        per = PERIODS["1h"]["dev"]
        t, tw = load(per[0][1], per[-1][2])
        r = evaluate("C45", t, per, mn, tw)
        m = r["book"]
        pg, pg_name = period_gate("C45", r, 0.75, 2, 3)
        g = {"≥200 trades": m.get("trades", 0) >= 200, "PF ≥ 1.15": m.get("pf", 0) >= 1.15,
             "PF ≥ 1.0 at 2x costs": r["book_x2"].get("pf", 0) >= 1.0, "DD ≤ 35%": m.get("max_dd_pct", 100) <= 35,
             pg_name: pg, "beats 95% of random twins": r.get("twin_pct", 0) >= 95,
             "top coin ≤ 20% of profit": (m.get("top_coin_share") or 1) <= 0.20}
        verdict = "PASS DEV" if all(g.values()) else "FAIL DEV"
    elif a.stage == "valid":
        if not has("dev", "PASS DEV"):
            raise SystemExit("no DEV pass recorded - VALID refused")
        per = PERIODS["1h"]["valid"]
        t, _ = load(per[0][1], per[-1][2])
        r = evaluate("C45", t, per, mn, None)
        m = r["book"]
        g = {"PF ≥ 1.10": m["pf"] >= 1.10, "profit": m["final"] > 300, "profit at 2x costs": r["book_x2"]["final"] > 300,
             "DD ≤ 40%": m["max_dd_pct"] <= 40}
        verdict = "PASS VALID" if all(g.values()) else "FAIL VALID"
    else:
        if not has("valid", "PASS VALID"):
            raise SystemExit("no VALID pass recorded - WALK-FORWARD refused")
        periods, need = WALK_FORWARD["1h"]
        t, _ = load(periods[0][1], periods[-1][2])
        r = evaluate("C45", t, periods, mn, None)
        pg, pg_name = period_gate("C45", r, 5 / 8, 3, need)
        g = {pg_name: pg}
        verdict = "PASS WALK-FORWARD" if pg else "FAIL WALK-FORWARD"
    r["extras"] = extras(t)
    ledger({"at": stamp, "batch": "C45", "family": "C45", "tf": "1h", "stage": a.stage, "result": r, "gates": g,
            "verdict": verdict})
    keys = ("book", "book_x2", "periods_detail", "by_cell", "all_signals", "extras", "twin_pct")
    print(json.dumps({k: r.get(k) for k in keys} | {"gates": g}, indent=1, default=str))
    print("VERDICT: C45", verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
