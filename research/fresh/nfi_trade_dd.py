"""Worst open loss vs final profit per NFI backtest trade, 3x vs 2x (2026-10-23, report only).

    .venv\\Scripts\\python.exe research\\fresh\\nfi_trade_dd.py

Worst open loss on margin = adverse move from the trade's final average entry (open_rate) to its worst price
(min_rate long / max_rate short) x leverage. Approximate: the average entry moves as NFI adds, so early in a trade
the real hole can differ.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
RUNS = {"3x": HERE / "nfi_bt_full223" / "chain_1m.json", "2x": HERE / "nfi_bt_full223_lev2" / "chain_1m.json"}


def load(path: Path) -> pd.DataFrame:
    df = pd.DataFrame([t for r in json.loads(path.read_text()) for t in r["trades"]])
    move = (df["max_rate"] / df["open_rate"] - 1).where(df["is_short"], 1 - df["min_rate"] / df["open_rate"])
    df["dd"] = -move.clip(lower=0) * df["leverage"]          # worst open loss on margin, negative
    df["pr"] = df["profit_ratio"]
    df["hours"] = df["trade_duration"] / 60
    return df


def report(name: str, df: pd.DataFrame) -> None:
    n = len(df)
    print(f"\n=== {name}: {n} trades, win {(df.pr > 0).mean():.1%}, median profit {df.pr.median():+.1%}")
    print("worst open loss on margin -> how many trades went that deep, and how they ended")
    for lo in (-0.10, -0.25, -0.40, -0.60, -0.80):
        d = df[df.dd <= lo]
        if not len(d):
            print(f"  <= {lo:.0%}: 0")
            continue
        print(f"  <= {lo:.0%}: {len(d):4d} ({len(d)/n:5.1%}) | ended in profit {(d.pr > 0).mean():5.1%} | "
              f"median final {d.pr.median():+6.1%} | worst final {d.pr.min():+6.1%} | median hours {d.hours.median():.0f}")
    rides = df[(df.dd <= -0.40) & (df.pr > 0) & (df.pr < 0.05)]
    print(f"  BTW-style (went <= -40%, ended 0..+5%): {len(rides)} ({len(rides)/n:.1%})")
    w = df[df.pr > 0]
    print(f"  winners: median worst open loss {w.dd.median():+.1%}, median profit {w.pr.median():+.1%}; "
          f"risk-to-reward (worst hole / final) median {(-w.dd / w.pr).median():.1f} to 1")


if __name__ == "__main__":
    for k, p in RUNS.items():
        report(k, load(p))
