"""Telegram alerts. Token + chat id come from secrets/telegram.json (token DPAPI-encrypted). Never raises."""
from __future__ import annotations

import logging
import urllib.parse
import urllib.request

from . import vault

log = logging.getLogger("trader")
_cfg: dict | None = None


def send(text: str) -> None:
    global _cfg
    try:
        if _cfg is None:
            _cfg = vault.get("telegram") or {}
        if not _cfg.get("token"):
            return
        data = urllib.parse.urlencode({"chat_id": _cfg["chat_id"], "text": text}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{_cfg['token']}/sendMessage", data=data, timeout=15).read()
    except Exception as e:
        log.warning("telegram not sent (%s)", type(e).__name__)
