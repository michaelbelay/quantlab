"""Bear batch 5 (X1-X6), step 1 signal test. Register: REGISTER_BEAR_IDEAS_2026-11-01_batch5.md.

    .venv\\Scripts\\python.exe research\\bear\\bear_batch5.py

Output: research/bear/batch5/trades_<idea>.csv, report.json. Nothing here is tuned after the run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bear_explore as bx  # noqa: E402  (19 coins, panels, bear flag)

OUT = HERE / "batch5"
ROOT = bx.ROOT
COINS, H, C, Hi, Lo, CUMF, FUND_AT, ELIG = bx.COINS, bx.H, bx.C, bx.Hi, bx.Lo, bx.CUMF, bx.FUND_AT, bx.ELIG
MID = pd.Timestamp("2024-05-01", tz="UTC")
COST = 0.002
N = len(H)
IDX = {c: k for k, c in enumerate(COINS)}
CL, HI, LO, CF = C.to_numpy(), Hi.to_numpy(), Lo.to_numpy(), CUMF.to_numpy()
BEAR_NEXT = bx.BEAR_CLOSE.to_numpy()           # next bar is on a bear day (known at this bar's close)
BEAR_NOW = bx.BEAR.to_numpy()
DAILY = np.asarray(H.hour == 23)


def leg(k, i, j, side):
    """gross + funding of one leg from close i to close j."""
    return side * (CL[j, k] / CL[i, k] - 1) - side * (CF[j, k] - CF[i, k])


def single(k, i, side, stop, hold=None, exit_mask=None):
    """one-coin trade; stop checked first; exit at the first close where exit_mask is true, or after hold bars."""
    e = CL[i, k]
    sp = e * (1 + stop) if side < 0 else e * (1 - stop)
    last = min(i + (hold or N), N - 1)
    j, px = last, CL[last, k]
    for jj in range(i + 1, last + 1):
        if np.isnan(CL[jj, k]):
            j = jj - 1
            if j == i:
                return None
            px = CL[j, k]
            break
        if (side < 0 and HI[jj, k] >= sp) or (side > 0 and LO[jj, k] <= sp):
            j, px = jj, sp
            break
        if exit_mask is not None and exit_mask[jj]:
            j, px = jj, CL[jj, k]
            break
    g = side * (px / e - 1) - side * (CF[j, k] - CF[i, k])
    return j, g - COST, g - 2 * COST


def pair(ks, kl, i, stop, hold, exit_fn=None):
    """short coin ks + long coin kl, same notional; pair stop on hourly closes; costs on both legs."""
    last = min(i + hold, N - 1)
    j = i
    for jj in range(i + 1, last + 1):
        if np.isnan(CL[jj, ks]) or np.isnan(CL[jj, kl]):
            break
        j = jj
        p = leg(ks, i, jj, -1) + leg(kl, i, jj, 1)
        if p <= -stop or (exit_fn is not None and exit_fn(jj)):
            break
    if j == i:
        return None
    g = leg(ks, i, j, -1) + leg(kl, i, j, 1)
    return j, g - 2 * COST, g - 4 * COST


def run_single(sig: np.ndarray, side, stop, hold=None, exit_mask=None, gap=0):
    rows = []
    s = sig & ELIG.to_numpy()
    for c in COINS:
        k = IDX[c]
        busy, last_e = -1, -10 ** 9
        for i in np.flatnonzero(s[:, k]):
            if i <= busy or i - last_e < gap:
                continue
            t = single(k, i, side, stop, hold, exit_mask)
            if t:
                busy, last_e = t[0], i
                rows.append((c, H[i], H[t[0]], t[1], t[2]))
    return pd.DataFrame(rows, columns=["coin", "entry", "exit", "net", "net2x"])


def stats(tr: pd.DataFrame) -> dict:
    if tr.empty:
        return {"trades": 0, "verdict": "🔴", "fails": "no trades"}
    a, b = tr[tr.entry < MID], tr[tr.entry >= MID]
    m = tr.groupby(tr.entry.dt.strftime("%Y-%m")).net.sum()
    s = {"trades": len(tr), "A": len(a), "B": len(b), "win": round(100 * (tr.net > 0).mean(), 1),
         "avg": round(100 * tr.net.mean(), 3), "avg_A": round(100 * a.net.mean(), 3) if len(a) else None,
         "avg_B": round(100 * b.net.mean(), 3) if len(b) else None, "avg_2x": round(100 * tr.net2x.mean(), 3),
         "months_pos": f"{int((m > 0).sum())}/{len(m)}",
         "years": {str(y): [len(g), round(100 * g.net.mean(), 2)] for y, g in tr.groupby(tr.entry.dt.year)},
         "worst": [(r.coin, str(r.entry)[:10], round(100 * r.net, 2)) for r in tr.nsmallest(3, "net").itertuples()],
         "best": [(r.coin, str(r.entry)[:10], round(100 * r.net, 2)) for r in tr.nlargest(3, "net").itertuples()]}
    f = []
    if len(tr) < 150 or len(a) < 50 or len(b) < 50:
        f.append("trade count")
    if not (len(a) and len(b) and a.net.mean() >= 0.003 and b.net.mean() >= 0.003):
        f.append("avg < +0.30% in a half")
    if tr.net2x.mean() <= 0:
        f.append("loses at 2x costs")
    if (m > 0).mean() < 0.55:
        f.append("months < 55%")
    s["verdict"], s["fails"] = ("🔴" if f else "🟠"), ", ".join(f)
    return s


def wide(v: np.ndarray) -> np.ndarray:
    return np.repeat(v[:, None], len(COINS), 1)


def rank_prev(s: pd.Series, n: int) -> pd.Series:
    """rank of the last value among the previous n values (0 = lowest)."""
    return s.rolling(n + 1, min_periods=n + 1).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    R = {}
    el = ELIG.to_numpy()

    # X1 bear spell: enter at the daily close that starts a spell, exit at the daily close that ends it
    start = DAILY & BEAR_NEXT & ~BEAR_NOW
    spell_end = DAILY & ~BEAR_NEXT
    R["X1_bear_spell_short"] = run_single(wide(start), -1, 0.15, exit_mask=spell_end)

    # X2 / X3 DVOL: at the daily close of day D use the row dated D-1
    d = pd.read_csv(ROOT / "data" / "market" / "dvol" / "BTC.csv").set_index("t").close
    d.index = pd.to_datetime(d.index, utc=True).normalize()
    d = d[~d.index.duplicated()].sort_index()
    use = H.normalize() - pd.Timedelta(days=1)
    prev = d.reindex(use).to_numpy()
    prev4 = d.reindex(use - pd.Timedelta(days=3)).to_numpy()
    rk = rank_prev(d, 90).reindex(use).to_numpy()
    x2 = DAILY & BEAR_NEXT & (prev / prev4 - 1 >= 0.15)
    x3 = DAILY & BEAR_NEXT & (rk <= 0.10)
    R["X2_dvol_rising"] = run_single(wide(x2), -1, 0.10, hold=120)
    R["X3_dvol_complacent"] = run_single(wide(x3), -1, 0.10, hold=168)

    # X4 perp-led rally: perp buy share high, spot buy share low, coin up >= 5% in 24h
    r24 = (C / C.shift(24) - 1).to_numpy()
    x4 = np.zeros((N, len(COINS)), bool)

    def bs_rank(path):
        f = pd.read_feather(path).drop_duplicates("date").set_index("date").sort_index()
        f.index = pd.to_datetime(f.index, utc=True)
        s = f.taker_buy_quote.rolling(24).sum() / f.quote_volume.rolling(24).sum()
        return rank_prev(s, 720).reindex(H).to_numpy()

    for c in COINS:
        fs = ROOT / "data" / "market" / "flow_spot" / f"{c}.feather"
        if not fs.exists():
            continue
        k = IDX[c]
        x4[:, k] = (r24[:, k] >= 0.05) & (bs_rank(ROOT / "data" / "market" / "flow" / f"{c}.feather") >= 0.70) & (bs_rank(fs) <= 0.30)
    R["X4_perp_led_rally"] = run_single(x4 & wide(BEAR_NEXT), -1, 0.08, hold=48, gap=24)

    # X5 carry pair: short coin + long BTC while the coin's funding is high
    fa = FUND_AT.to_numpy()
    kb = IDX["BTC"]
    rows = []
    for c in COINS:
        if c == "BTC":
            continue
        k = IDX[c]
        busy = -1
        lowf = ~np.isnan(fa[:, k]) & (fa[:, k] < 0.0001)
        for i in np.flatnonzero(~np.isnan(fa[:, k]) & (fa[:, k] >= 0.0003) & BEAR_NEXT & el[:, k] & el[:, kb]):
            if i <= busy:
                continue
            t = pair(k, kb, i, 0.10, 168, lambda j, lowf=lowf: lowf[j])
            if t:
                busy = t[0]
                rows.append((c, H[i], H[t[0]], t[1], t[2]))
    R["X5_carry_pair"] = pd.DataFrame(rows, columns=["coin", "entry", "exit", "net", "net2x"])

    # X6 xs momentum pairs at the Sunday daily close
    r30 = (C / C.shift(720) - 1).to_numpy()
    rows = []
    for i in np.flatnonzero(DAILY & BEAR_NEXT & np.asarray(H.dayofweek == 6)):
        idx = np.flatnonzero(el[i] & ~np.isnan(r30[i]))
        if len(idx) < 6:
            continue
        order = idx[np.argsort(r30[i, idx])]
        for w, s in zip(order[:3], order[::-1][:3]):
            t = pair(w, s, i, 0.15, 168)
            if t:
                rows.append((f"{COINS[w]}/{COINS[s]}", H[i], H[t[0]], t[1], t[2]))
    R["X6_xs_momentum_pair"] = pd.DataFrame(rows, columns=["coin", "entry", "exit", "net", "net2x"])

    rep = {}
    for k, tr in R.items():
        tr.sort_values("net").to_csv(OUT / f"trades_{k}.csv", index=False)
        rep[k] = stats(tr)
        print(k, json.dumps(rep[k], ensure_ascii=False))
    (OUT / "report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
