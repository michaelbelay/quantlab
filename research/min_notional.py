"""What is the smallest order Binance USDT-M futures will accept, per pair?

Why this exists: on 2026-09-23 the demo venue REJECTED a 50 USDT BTC order --
its minimum notional is 75 USDT there. If mainnet minimums are anywhere near
that, a 15 USDT position size is not executable and the 300 USDT starting
capital plan is wrong. This asks the MAINNET exchange itself (public endpoint,
no credentials, no orders) for every pair in the live universe.

    python research/min_notional.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STAKE = 15.0   # the planned per-position stake, USDT
LEV = 1        # notional = stake * leverage; we size at 1x


def main() -> int:
    import ccxt
    cfg = json.loads((ROOT / "configs" / "universe_coins.json").read_text(encoding="utf-8"))
    pairs = cfg["pair_whitelist"]

    ex = ccxt.binance({"options": {"defaultType": "swap"}})
    ex.load_markets()

    rows, missing = [], []
    for p in pairs:
        m = ex.markets.get(p)
        if m is None:
            missing.append(p)
            continue
        lim = m.get("limits", {})
        cost_min = (lim.get("cost") or {}).get("min")
        amt_min = (lim.get("amount") or {}).get("min")
        # ccxt normalises MIN_NOTIONAL into limits.cost.min; keep the raw filter
        # too, because that is what the matching engine actually enforces.
        raw = {f["filterType"]: f for f in m["info"].get("filters", [])}
        notional = raw.get("MIN_NOTIONAL", {}).get("notional")
        rows.append({
            "pair": p,
            "cost_min": float(cost_min) if cost_min is not None else None,
            "notional_filter": float(notional) if notional is not None else None,
            "amount_min": float(amt_min) if amt_min is not None else None,
        })

    def floor(r):
        vals = [v for v in (r["cost_min"], r["notional_filter"]) if v is not None]
        return max(vals) if vals else None

    out = ROOT / "research" / "results" / "min_notional_mainnet.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"stake": STAKE, "rows": rows, "missing": missing}, indent=2), encoding="utf-8")

    blocked = [r for r in rows if (floor(r) or 0) > STAKE * LEV]
    ok = [r for r in rows if (floor(r) or 0) <= STAKE * LEV]
    unknown = [r for r in rows if floor(r) is None]

    print(f"pairs in universe:            {len(pairs)}")
    print(f"not listed on mainnet swap:   {len(missing)}  {missing if missing else ''}")
    print(f"minimum known:                {len(rows) - len(unknown)}")
    print(f"tradeable at {STAKE:.0f} USDT:        {len(ok)}")
    print(f"BLOCKED at {STAKE:.0f} USDT:          {len(blocked)}")
    if blocked:
        print()
        print(f"{'pair':<22}{'floor USDT':>12}")
        for r in sorted(blocked, key=lambda r: -(floor(r) or 0)):
            print(f"{r['pair']:<22}{floor(r):>12.2f}")
    # the distribution matters more than the count
    fl = sorted(floor(r) for r in rows if floor(r) is not None)
    if fl:
        print()
        print(f"floor min/median/max: {fl[0]:.2f} / {fl[len(fl)//2]:.2f} / {fl[-1]:.2f} USDT")
    print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
