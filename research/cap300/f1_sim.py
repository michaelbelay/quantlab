"""300 USDT account simulation of F1 crash bounce (flush_f1.py), 2026-10-09.
Same design and pass rule as channel_sim.py (fixed before running): 300 USDT, 1x, K = 5 slots (3 / 10 info),
position = realised equity / K, Binance minimum notional, same-hour signals shuffled (20 seeds), one position per coin.
Pass: median final > 300, >= 4 of 6 years positive, median max drawdown < 40%.
Unseen trades = research/unseen3/trades_flush_f1.parquet (the pre-registered run). Dev coins shown in-sample.
Exit time = close of the exit bar (entry bar open + (exit - ent + 1) hours).
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "research" / "cap300")]
import channel_sim as C  # noqa: E402

D, I = C.D, C.I


def to_account(t):
    t = t.copy()
    t["entry"] = pd.to_datetime(t["date"], utc=True)
    t["exit"] = t.entry + pd.to_timedelta(t["exit"] - t["ent"] + 1, unit="h")
    return t[["coin", "entry", "exit", "pnl"]].reset_index(drop=True)


def main():
    minn = C.min_notionals()
    C.report("F1 on UNSEEN coins (main)", to_account(pd.read_parquet(ROOT / "research" / "unseen3" / "trades_flush_f1.parquet")), minn)
    m = I.load_idea(ROOT / "research" / "incubator" / "ideas" / "flush_f1.py")
    dev = I.rule_trades(D.Universe(D.dev_files()), m, C.market_types(), C.A, C.B)
    C.report("F1 on development coins (in-sample, comparison)", to_account(dev), minn)


if __name__ == "__main__":
    main()
