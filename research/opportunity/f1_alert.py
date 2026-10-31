"""F1 crash-bounce alert (🟠 weak signal), run by scan.py after every scan. Nothing is traded.

Uses exactly the frozen incubator idea research/incubator/ideas/flush_f1.py (same signals, same market-type rule:
the entry day must be a DN day) on the scanner's live_cache. Writes f1_alerts.json (UI) and sends one toast per
new crash event. Forward results of these signals are measured by the incubator (idea flush_f1), not here.
Evidence: research/UNSEEN3_RESULT_2026-10-09.md and research/cap300/F1_300_RESULT_2026-10-09.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / "research"), str(ROOT / "research" / "incubator")]
import downtrend as D  # noqa: E402
import incubator as I  # noqa: E402

OUT = HERE / "f1_alerts.json"
FRESH_H = 3            # signal bars of the last 3 closed hours count as new
SHOW_H = 24            # alerts stay visible for one holding period
WHY = ["🟠 weak signal: real on 280 unseen coins (positive all 6 years) but lottery-like",
       "most profit came from a few huge bounces; without the 3 biggest trades a 300 USDT account lost",
       "you decide; size small"]


def scan() -> dict:
    m = I.load_idea(ROOT / "research" / "incubator" / "ideas" / "flush_f1.py")
    types = I.live_types()
    now = pd.Timestamp.now(tz="UTC").floor("h")
    today = types.get(now.floor("D"))
    found = []
    for coin, p, fp in I.live_files():
        try:
            d = D.load_coin(p, fp)
        except Exception:
            continue
        if d is None or len(d) < 30:
            continue
        g = d.tail(SHOW_H + 1)
        sig = m.signals(g).fillna(False)
        for t in g.index[sig.to_numpy(bool)]:
            ent = t + pd.Timedelta(hours=1)
            ty = types.get(ent.floor("D"))
            if not isinstance(ty, str) or not ty.startswith(m.MARKET):
                continue
            r = d.loc[t]
            ref = float(d.open.get(ent, np.nan)) if ent in d.index else float(r.close)
            found.append({"coin": coin, "signal_bar": str(t), "entry_time": str(ent), "hours_ago": int((now - t) / pd.Timedelta(hours=1)) - 1,
                          "ref_price": ref, "last_price": float(d.close.iloc[-1]),
                          "stop": ref * (1 - m.STOP_K * float(r.sigma)), "stop_pct": m.STOP_K * float(r.sigma) * 100,
                          "exit_by": str(ent + pd.Timedelta(hours=m.HOLD)), "ret24_pct": float(r.ret24) * 100,
                          "vol_x": float(r.vol24 / r.vol24_avg30) if r.vol24_avg30 else None,
                          "dv30": float(r.dv30) if pd.notna(r.dv30) else 0.0, "market_type": ty})
    found.sort(key=lambda a: (a["hours_ago"], -a["dv30"]))
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"history": []}
    seen = {(h["coin"], h["signal_bar"]) for h in old.get("history", [])}
    new = [a for a in found if (a["coin"], a["signal_bar"]) not in seen and a["hours_ago"] < FRESH_H]
    hist = old.get("history", []) + [{k: a[k] for k in ("coin", "signal_bar", "ref_price", "stop", "exit_by", "market_type")}
                                     for a in found if (a["coin"], a["signal_bar"]) not in seen]
    state = {"updated": str(pd.Timestamp.now(tz="UTC").floor("min")), "market_type_today": today,
             "active_when": "only on DN days (BTC daily close below its 50-day average)", "why": WHY,
             "rule": "coin down >= 2.5 sigma in 24h on >= 3x its normal volume -> long next hour, stop 1.5 sigma, exit after 24h",
             "alerts": found, "history": hist}
    OUT.write_text(json.dumps(state, indent=1, default=str), encoding="utf-8")
    if new:
        import forward as FW
        top = ", ".join(a["coin"] for a in new[:4])
        FW.notify(f"🟠 Crash bounce (F1): {len(new)} coin{'s' if len(new) > 1 else ''}",
                  f"{top}. Long, stop ~{new[0]['stop_pct']:.1f}%, exit after 24h. Weak, lottery-like signal - you decide.")
    return {"alerts": len(found), "new": len(new), "market_type_today": today}


if __name__ == "__main__":
    print(scan())
