"""Danger switch study (2026-10-08), development coins only, 2021-01-01..2026-09-19.

Switch (fixed before running): DANGER at hour h when >= 70% of coins (with data) have a negative 24h return at the
close of bar h. Long trades whose signal bar is in DANGER are skipped. 60% / 80% are printed for information only.

Useful (fixed before running), per long strategy: trades in DANGER have a negative day-average AND skipping them
raises the day-average in >= 4 of the 6 years. Strategies: volume absorption (incubator idea), channel 602db68df71a,
streak 9ef3c32f80d4, and a plain "long every coin for 24h at 00:00 UTC" baseline (the question itself: are longs
after a broad sell-off worse or better than usual?).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "research"), str(ROOT / "research" / "incubator")]
import downtrend as D  # noqa: E402
import incubator as I  # noqa: E402
from regime_switch import market_types  # noqa: E402

A, B = "2021-01-01", "2026-09-19"
LEVELS = [0.6, 0.7, 0.8]
MAIN = 0.7


def breadth(U) -> pd.Series:
    g = U.g
    neg = pd.Series(np.where(U.ok, (g.ret24 < 0).astype(float), np.nan), index=g.index)
    b = neg.groupby(U.date.to_numpy()).mean()
    n = pd.Series(U.ok, index=g.index).groupby(U.date.to_numpy()).sum()
    b[n < 20] = np.nan                                     # too few coins for a market reading
    b.index = pd.to_datetime(b.index, utc=True)
    return b


def table(name, tr, sig_time, br):
    """tr: pnl (%), day, date; sig_time: time of the signal bar (breadth read at its close)."""
    x = br.reindex(pd.to_datetime(sig_time, utc=True)).to_numpy()
    tr = tr.assign(br=x).dropna(subset=["br"])
    def dayavg(t):
        return t.pnl.groupby(t.day).mean().mean() if len(t) else np.nan
    print(f"\n== {name}: {len(tr)} trades, day avg {dayavg(tr):+.3f}%")
    for lv in LEVELS:
        d, n = tr[tr.br >= lv], tr[tr.br < lv]
        yrs = []
        for y in range(2021, 2027):
            ty = tr[tr.date.dt.year == y]
            if len(ty) >= 20:
                yrs.append(dayavg(ty[ty.br < lv]) > dayavg(ty))
        tag = " <- MAIN" if lv == MAIN else ""
        useful = (dayavg(d) < 0) and sum(yrs) >= 4
        print(f"  level {lv:.0%}: danger {len(d):5d} trades ({len(d)/len(tr):5.1%}) day avg {dayavg(d):+.3f}% | "
              f"normal {len(n):5d} day avg {dayavg(n):+.3f}% | with switch {dayavg(n):+.3f}% vs {dayavg(tr):+.3f}% | "
              f"years improved {sum(yrs)}/{len(yrs)} | useful {'YES' if useful else 'no'}{tag}")


def main():
    U = D.Universe(D.dev_files())
    br = breadth(U)
    print(f"breadth hours {br.notna().sum()}, share of hours in danger: " +
          ", ".join(f"{lv:.0%}: {(br >= lv).mean():.1%}" for lv in LEVELS))

    # volume absorption (as frozen in the incubator, MARKET UP)
    m = I.load_idea(ROOT / "research" / "incubator" / "ideas" / "absorption_up.py")
    tr = I.rule_trades(U, m, market_types(), A, B)
    table("volume absorption (UP, long 48h)", tr, U.date.iloc[tr.ent.to_numpy() - 1].to_numpy(), br)

    # pipeline candidates (dev trade files, all market types; entry = open of the bar after the signal)
    for cid, nm in [("602db68df71a", "channel"), ("9ef3c32f80d4", "streak")]:
        t = pd.read_parquet(ROOT / "research" / "pipeline" / "trades" / f"{cid}__dev.parquet")
        t = t[(t.side == "long") & (t.entry_date >= pd.Timestamp(A, tz="UTC")) & (t.entry_date < pd.Timestamp(B, tz="UTC"))]
        t = pd.DataFrame({"pnl": t.pnl / t.notional * 100, "date": t.entry_date.astype("datetime64[ns, UTC]")})
        t["day"] = t.date.dt.floor("D")
        table(f"{nm} {cid} (long trades, all days)", t, t.date - pd.Timedelta(hours=1), br)

    # baseline: long every coin 24h from the 00:00 open, signal bar = 23:00 the day before, 0.2% cost
    g = U.g
    c = g.close.to_numpy(float)
    o = g.open.to_numpy(float)
    idx = np.flatnonzero((U.date.dt.hour == 0).to_numpy() & U.ok)
    idx = idx[idx + 24 < len(g)]
    same = (g.coin.to_numpy()[idx + 23] == g.coin.to_numpy()[idx]) & (idx >= 1)
    idx = idx[same]
    pnl = (c[idx + 23] / o[idx] - 1) * 100 - 0.2
    t = pd.DataFrame({"pnl": pnl, "date": U.date.iloc[idx].to_numpy()})
    t["date"] = pd.to_datetime(t.date, utc=True)
    t = t[(t.date >= pd.Timestamp(A, tz="UTC")) & (t.date < pd.Timestamp(B, tz="UTC")) & np.isfinite(t.pnl)]
    t["day"] = t.date.dt.floor("D")
    table("baseline: long every coin 24h at 00:00", t, t.date - pd.Timedelta(hours=1), br)


if __name__ == "__main__":
    main()
