r"""Put closed PAPER trades back where the rule closed them, for exits that were written late.

    .venv\Scripts\python.exe -m trader repair paper            show what would change (writes nothing)
    .venv\Scripts\python.exe -m trader repair paper --apply    write it

Why: until 2026-11-12 a paper exit was filled at whatever the price was when the trader noticed. After the
2026-11-03 reboot nobody was running for 8 days, so on 2026-11-11 HYPE was booked as a stop at 73.1 (its stop was
never touched inside its 48 hours) and NEAR as a time exit at the price of a week later. This walks each closed
trade's candles with the same code the trader now uses (PaperBroker.audit) and moves an exit that was recorded more
than 10 minutes after the rule made it. The old values are kept in the row's note. Rows are costed the way they
were opened (fee only; slippage and funding start with the trades opened after this change).
"""
from __future__ import annotations

import pandas as pd

from .broker import PaperBroker
from .market import exchange
from .settings import FEE, PAPER_WALLET, RUNTIME
from .store import Store, utcnow

FMT = "%Y-%m-%d %H:%M:%S"


def find(store: Store, broker: PaperBroker) -> list[dict]:
    out = []
    for t in store.closed_trades():
        if "repaired" in (t.get("note") or ""):
            continue
        closed = pd.Timestamp(t["close_time"], tz="UTC")
        hit = broker._replay(t, closed)
        if not hit or hit[1] is None or closed - hit[2] <= pd.Timedelta(minutes=10):
            continue
        reason, px, when = hit
        fees = t["stake"] * FEE + t["amount"] * px * FEE
        move = (t["open_price"] - px) if t["short"] else (px - t["open_price"])
        out.append({"t": t, "reason": reason, "price": px, "when": when.strftime(FMT), "fees": fees,
                    "pnl": move * t["amount"] - fees})
    return out


def main(mode: str = "paper", apply: bool = False) -> int:
    if mode != "paper":
        print("repair is for the paper book only - live exits are real fills")
        return 1
    store = Store(RUNTIME / "paper.sqlite", PAPER_WALLET)
    fixes = find(store, PaperBroker(exchange(), store))
    if not fixes:
        print("nothing to repair: every closed trade was closed when the rule closed it")
        return 0
    delta = 0.0
    for f in fixes:
        t = f["t"]
        delta += f["pnl"] - t["pnl"]
        print(f"#{t['id']} {t['coin']} {'short' if t['short'] else 'long'}: recorded {t['reason']} at {t['close_price']:.6g} "
              f"on {t['close_time']} ({t['pnl']:+.2f})  ->  rule: {f['reason']} at {f['price']:.6g} on {f['when']} ({f['pnl']:+.2f})")
        if apply:
            store.close(t["id"], f["price"], f["reason"], f["fees"], f["pnl"], when=f["when"],
                        note=f"repaired {utcnow()}: trader was down; was {t['reason']} at {t['close_price']:.6g} "
                             f"on {t['close_time']}, pnl {t['pnl']:+.2f}")
    print(f"paper wallet changes by {delta:+.2f} USDT" + ("  - written" if apply else "  - nothing written, add --apply"))
    return 0
