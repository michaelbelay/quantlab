"""Trade records (sqlite), one database per mode: data/trader/paper.sqlite, data/trader/live.sqlite."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coin TEXT NOT NULL, short INTEGER NOT NULL,
    signal_time TEXT NOT NULL, sig24 REAL NOT NULL,
    open_time TEXT NOT NULL, open_price REAL NOT NULL, amount REAL NOT NULL, stake REAL NOT NULL,
    stop_price REAL NOT NULL, stop_order_id TEXT,
    close_time TEXT, close_price REAL, reason TEXT,
    fees REAL NOT NULL DEFAULT 0, pnl REAL
);
CREATE TABLE IF NOT EXISTS wallet (k TEXT PRIMARY KEY, v REAL NOT NULL);
"""
# Columns added after the first version. funding: USDT paid (+) or received (-) while the trade was open, already
# inside pnl. note: anything unusual about the row (late exit rebuilt from candles, stop order missing, ...).
ADDED = {"funding": "REAL NOT NULL DEFAULT 0", "note": "TEXT"}


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class Store:
    def __init__(self, path: Path, start_wallet: float | None = None):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with closing(self._db()) as db, db:
            db.executescript(SCHEMA)
            have = {r[1] for r in db.execute("PRAGMA table_info(trades)")}
            for col, kind in ADDED.items():
                if col not in have:
                    db.execute(f"ALTER TABLE trades ADD COLUMN {col} {kind}")
            if start_wallet is not None:
                db.execute("INSERT OR IGNORE INTO wallet VALUES ('start', ?)", (start_wallet,))

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def open_trades(self) -> list[dict]:
        with closing(self._db()) as db:
            return [dict(r) for r in db.execute("SELECT * FROM trades WHERE close_time IS NULL ORDER BY id")]

    def closed_trades(self) -> list[dict]:
        with closing(self._db()) as db:
            return [dict(r) for r in db.execute("SELECT * FROM trades WHERE close_time IS NOT NULL ORDER BY id")]

    def add(self, **t) -> int:
        cols = ", ".join(t)
        with closing(self._db()) as db, db:
            return db.execute(f"INSERT INTO trades ({cols}) VALUES ({', '.join('?' * len(t))})", tuple(t.values())).lastrowid

    def close(self, tid: int, price: float, reason: str, fees: float, pnl: float, when: str | None = None,
              funding: float = 0.0, note: str | None = None) -> None:
        """when: the UTC time the exit really happened, if that is not now (an exit rebuilt from candles)."""
        with closing(self._db()) as db, db:
            db.execute("UPDATE trades SET close_time=?, close_price=?, reason=?, fees=?, pnl=?, funding=?, "
                       "note=COALESCE(?, note) WHERE id=?", (when or utcnow(), price, reason, fees, pnl, funding, note, tid))

    def annotate(self, tid: int, note: str) -> None:
        with closing(self._db()) as db, db:
            db.execute("UPDATE trades SET note=? WHERE id=?", (note, tid))

    def realized(self, day: str) -> float:
        """Closed profit of one UTC day ('YYYY-MM-DD')."""
        with closing(self._db()) as db:
            return float(db.execute("SELECT COALESCE(SUM(pnl), 0) FROM trades WHERE substr(close_time, 1, 10)=?",
                                    (day,)).fetchone()[0])

    def last_signal(self, coin: str, short: bool) -> str | None:
        with closing(self._db()) as db:
            r = db.execute("SELECT MAX(signal_time) FROM trades WHERE coin=? AND short=?", (coin, int(short))).fetchone()
            return r[0]

    def paper_balance(self) -> float:
        """Paper only: start wallet + closed profit."""
        with closing(self._db()) as db:
            start = db.execute("SELECT v FROM wallet WHERE k='start'").fetchone()[0]
            pnl = db.execute("SELECT COALESCE(SUM(pnl), 0) FROM trades WHERE close_time IS NOT NULL").fetchone()[0]
            return float(start) + float(pnl)
