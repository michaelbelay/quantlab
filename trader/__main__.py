r"""quantlab trader - FlowTrend on Binance USD-M.

    .venv\Scripts\python.exe -m trader run paper        paper trading (no keys, no real orders)
    .venv\Scripts\python.exe -m trader run live         real orders (needs: python -m trader.vault set binance)
    .venv\Scripts\python.exe -m trader status paper
    .venv\Scripts\python.exe -m trader pause paper      no new entries, open trades still managed
    .venv\Scripts\python.exe -m trader resume paper
    .venv\Scripts\python.exe -m trader replay           re-check the signal code on saved history
"""
from __future__ import annotations

import sys

import pandas as pd

from .engine import Engine, get_state, set_state, setup_logging
from .market import exchange, last_prices
from .settings import PAPER_WALLET, RUNTIME
from .store import Store


def status(mode: str) -> None:
    st = Store(RUNTIME / f"{mode}.sqlite", PAPER_WALLET if mode == "paper" else None)
    op, cl = st.open_trades(), st.closed_trades()
    px = last_prices(exchange(), [t["coin"] for t in op]) if op else {}
    rows = []
    for t in op:
        p = px.get(t["coin"], t["open_price"])
        u = ((t["open_price"] - p) if t["short"] else (p - t["open_price"])) * t["amount"] - t["fees"]
        rows.append((u, t, p))
    hb = RUNTIME / f"{mode}_heartbeat.txt"
    print(f"{mode}: {get_state(mode)}, last heartbeat {hb.read_text() if hb.exists() else 'never'} UTC")
    closed = sum(t["pnl"] for t in cl)
    print(f"closed: {len(cl)} trades, {closed:+.2f} USDT   open: {len(op)} trades, {sum(r[0] for r in rows):+.2f} USDT")
    for u, t, p in sorted(rows, key=lambda r: r[0]):                  # worst first
        print(f"  {t['coin']:<9}{'short' if t['short'] else 'long':<6} in {t['open_price']:.6g} now {p:.6g} "
              f"stop {t['stop_price']:.6g}  {u:+.2f} USDT  opened {t['open_time']} UTC")
    for t in cl[-5:]:
        print(f"  closed {t['coin']} {'short' if t['short'] else 'long'} {t['reason']} {t['pnl']:+.2f}")


def main(a: list[str]) -> int:
    if len(a) >= 2 and a[0] == "run" and a[1] in ("paper", "live"):
        setup_logging(a[1])
        Engine(a[1]).run()
    elif len(a) >= 2 and a[0] == "status":
        status(a[1])
    elif len(a) >= 2 and a[0] in ("pause", "resume"):
        set_state(a[1], "paused" if a[0] == "pause" else "running")
        print(a[1], get_state(a[1]))
    elif a[:1] == ["replay"]:
        from .replay import main as replay
        replay()
    else:
        print(__doc__)
        return 1
    return 0


sys.exit(main(sys.argv[1:]))
