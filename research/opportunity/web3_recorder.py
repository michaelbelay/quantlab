"""Record Binance Web3 market boards every hour, so they can be tested later (they have no history API).

Boards (public web3.binance.com endpoints, the same ones the Binance Skills Hub skills call; no key):
  trending      token-rank rankType 10, 24h, per chain (BSC, Solana, Base, Ethereum), top 50
  inflow        smart-money net-inflow rank, 24h, per chain (BSC, Solana, Base)
  hype          social-hype leaderboard, 24h, per chain (BSC, Solana, Base), with sentiment
  sm_signal     smart-money buy signals (BSC, Solana), latest 100 each, keyed by signalId

Stored raw in web3_feed.db (one row per item per snapshot). Pre-registered test: PREREGISTRATION_2026-10-07_web3.md.
Run:  .venv\\Scripts\\python.exe research\\opportunity\\web3_recorder.py      (also called by scan.py --auto)
"""
from __future__ import annotations

import json
import sqlite3
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
DB = HERE / "web3_feed.db"
BASE = "https://web3.binance.com/bapi/defi"
UA = {"Accept-Encoding": "identity", "User-Agent": "binance-web3/3.0 (Skill)", "content-type": "application/json"}
CHAINS = {"56": "BSC", "CT_501": "SOL", "8453": "BASE", "1": "ETH"}


def call(url: str, body: dict | None = None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers=UA, method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def _trending(c):
    r = call(f"{BASE}/v1/public/wallet-direct/buw/wallet/market/token/pulse/unified/rank/list/ai",
             {"rankType": 10, "chainId": c, "period": 50, "page": 1, "size": 50, "countMin": 10, "launchTimeMin": 15,
              "liquidityMin": 5000, "uniqueTraderMin": 10, "volumeMin": 10000, "tagFilter": [1, 2, 3]})
    return [(t.get("symbol"), t.get("contractAddress"), t) for t in (r.get("data") or {}).get("tokens") or []]


def _inflow(c):
    r = call(f"{BASE}/v1/public/wallet-direct/tracker/wallet/token/inflow/rank/query/ai",
             {"chainId": c, "period": "24h", "tagType": 2})
    d = sorted(r.get("data") or [], key=lambda x: -float(x.get("inflow") or 0))
    return [(t.get("tokenName"), t.get("ca"), t) for t in d]


def _hype(c):
    r = call(f"{BASE}/v1/public/wallet-direct/buw/wallet/market/token/pulse/social/hype/rank/leaderboard/ai?"
             f"chainId={c}&targetLanguage=en&timeRange=1&sentiment=All&socialLanguage=ALL")
    return [((t.get("metaInfo") or {}).get("symbol"), (t.get("metaInfo") or {}).get("contractAddress"), t)
            for t in (r.get("data") or {}).get("leaderBoardList") or []]


def _signals(c):
    r = call(f"{BASE}/v1/public/wallet-direct/buw/wallet/web/signal/smart-money/ai", {"chainId": c, "page": 1, "pageSize": 100})
    return [(t.get("ticker"), t.get("contractAddress"), t) for t in r.get("data") or []]


JOBS = ([("trending", c, _trending) for c in ("56", "CT_501", "8453", "1")]
        + [("inflow", c, _inflow) for c in ("56", "CT_501", "8453")]
        + [("hype", c, _hype) for c in ("56", "CT_501", "8453")]
        + [("sm_signal", c, _signals) for c in ("56", "CT_501")])


def record() -> str:
    ts = int(time.time())
    c = sqlite3.connect(DB, timeout=30)
    c.execute("""CREATE TABLE IF NOT EXISTS snap (ts INTEGER, board TEXT, chain TEXT, rank INTEGER, symbol TEXT,
                 contract TEXT, data TEXT)""")
    c.execute("CREATE INDEX IF NOT EXISTS snap_ts ON snap(ts, board)")
    n, errors = 0, []
    for board, chain, fn in JOBS:                   # one failing board must not stop the others
        try:
            items = fn(chain)
        except Exception as e:
            errors.append(f"{board}/{CHAINS[chain]}: {type(e).__name__}")
            continue
        c.executemany("INSERT INTO snap VALUES (?,?,?,?,?,?,?)",
                      [(ts, board, CHAINS[chain], i, sym, ca, json.dumps(item, separators=(",", ":")))
                       for i, (sym, ca, item) in enumerate(items, 1)])
        n += len(items)
    c.commit()
    c.close()
    return f"web3 recorder: {n} rows" + (f", errors {errors}" if errors else "")


if __name__ == "__main__":
    print(record())
