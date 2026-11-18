"""Small file helpers. A status file must never be seen half-written: a reboot in the middle of a plain
write_text left 19 NUL bytes in the heartbeat on 2026-11-03 and took the Trader tab down for days."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path


def write_atomic(path: Path, text: str) -> None:
    """Write to <name>.tmp, flush to disk, then swap it in. Readers see the old or the new text, never a mix."""
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    for i in range(6):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:                 # Windows: someone has the target open for a moment
            time.sleep(0.05 * (i + 1))
    os.replace(tmp, path)


def read_time(path: Path) -> datetime | None:
    """A 'YYYY-MM-DD HH:MM:SS' UTC stamp from a file, or None when it is missing, empty or damaged."""
    try:
        return datetime.strptime(path.read_text(encoding="utf-8", errors="replace").strip()[:19],
                                 "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except (OSError, ValueError):
        return None


def age_min(path: Path) -> float | None:
    t = read_time(path)
    return None if t is None else round((datetime.now(timezone.utc) - t).total_seconds() / 60, 1)
