"""Delisting-short paper bot (2026-10-25) - no keys, no orders. Rule: ../REGISTER_DELIST_2026-10-25.md, variant D2.

    .venv\\Scripts\\python.exe research\\fresh\\delist\\paper.py

Every minute: read Binance's public "Delisting" announcements; for each NEW spot or futures delisting that names a
coin with a live USDT-M perp, paper-short 30 USDT notional at the close of the first full 5m candle after the news;
exit after 72 h or at +15% (5m high). Announcements present at the first start are only marked as seen.
Output: state.json (open + closed), log.txt, REPORT.md.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ST = HERE / "paper_state.json"
STOP, HOLD_MS, COST, NOTION = 0.15, 72 * 3600 * 1000, 0.003, 30.0
LIST = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=161&pageNo=1&pageSize=20"
SKIP = {"USD", "M", "BUSD", "USDT", "USDC", "TUSD", "FDUSD", "UP", "DOWN", "COIN", "SUSD", "USDP", "DAI", "EUR"}


def log(msg: str) -> None:
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}"
    print(line, flush=True)
    with (HERE / "paper_log.txt").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def get(url: str):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read())


def coins(title: str) -> list[str]:
    if not (title.startswith("Binance Will Delist") or title.startswith("Binance Futures Will Delist")):
        return []
    body = re.sub(r"\(.*?\)|on \d{4}-\d{2}-\d{2}.*$|USDⓈ-M|USDT-Margined|Perpetual|Contracts?|and|Binance Futures Will Delist|"
                  r"Binance Will Delist|Multiple", " ", title)
    out = []
    for k in re.findall(r"\b[0-9A-Z]{2,15}\b", body):
        k = re.sub(r"(USDT|BUSD|USDC)$", "", k) or k
        if k not in SKIP and not k.endswith(("UP", "DOWN", "BULL", "BEAR")) and k not in out:
            out.append(k)
    return out


def k5(sym: str, start_ms: int) -> list:
    return get(f"https://fapi.binance.com/fapi/v1/klines?symbol={sym}&interval=5m&startTime={start_ms}&limit=1000")


def step(s: dict) -> None:
    arts = get(LIST)["data"]["catalogs"][0]["articles"]
    first = not s.get("seen")
    perps = None
    for a in arts:
        key = str(a["id"])
        if key in s.setdefault("seen", {}):
            continue
        s["seen"][key] = a["title"]
        if first:
            continue
        cs = coins(a["title"])
        if not cs:
            continue
        if perps is None:
            perps = {x["symbol"] for x in get("https://fapi.binance.com/fapi/v1/exchangeInfo")["symbols"] if x.get("status") == "TRADING"}
        for c in cs:
            sym = c + "USDT"
            if sym in perps and sym not in s.setdefault("done_syms", []):
                s["done_syms"].append(sym)
                s.setdefault("pending", []).append({"sym": sym, "news_ms": a["releaseDate"], "title": a["title"]})
                log(f"NEW delisting: {sym} ({a['title']}) - paper short at the next 5m close")
    if first:
        log(f"first start: {len(s['seen'])} existing announcements marked as seen")
    now = time.time() * 1000
    for p in list(s.get("pending", [])):
        start = (p["news_ms"] // 300000 + 1) * 300000                     # first full 5m candle after the news
        if now < start + 300000 + 5000:
            continue
        ks = [k for k in k5(p["sym"], start) if k[0] == start]
        if not ks:
            continue
        e = float(ks[0][4])
        s.setdefault("open", []).append({**p, "entry_ms": start + 300000, "entry": e})
        s["pending"].remove(p)
        log(f"OPEN paper short {p['sym']} @ {e}")
    for t in list(s.get("open", [])):
        ks = [k for k in k5(t["sym"], t["entry_ms"]) if k[6] < now]
        res, end = None, None
        for k in ks:
            if float(k[2]) >= t["entry"] * (1 + STOP):
                res, end, why = -STOP, k[6], "stop"
                break
            if k[6] + 1 >= t["entry_ms"] + HOLD_MS:
                res, end, why = -(float(k[4]) / t["entry"] - 1), k[6], "time"
                break
        last = float(ks[-1][4]) if ks else t["entry"]
        t["now"], t["open_usdt"] = last, round((-(last / t["entry"] - 1) - COST) * NOTION, 2)
        if res is not None:
            s["open"].remove(t)
            s.setdefault("closed", []).append({**t, "exit_ms": end, "net": res - COST, "usdt": round((res - COST) * NOTION, 2), "exit": why})
            log(f"CLOSE {t['sym']} {why} {round((res - COST) * 100, 2)}% = {round((res - COST) * NOTION, 2)} USDT")


def report(s: dict) -> None:
    cl, op = s.get("closed", []), s.get("open", [])
    f = lambda ms: datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M")  # noqa: E731
    md = ["# Delisting-short paper bot", "", f"Updated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC. Paper only, 30 USDT notional per event.", "",
          f"- closed {len(cl)}: {sum(x['usdt'] for x in cl):+.2f} USDT · open {len(op)}: {sum(x.get('open_usdt', 0) for x in op):+.2f} USDT · waiting {len(s.get('pending', []))}", ""]
    md += [f"- OPEN {t['sym']} since {f(t['entry_ms'])} @ {t['entry']} now {t.get('now')} -> {t.get('open_usdt', 0):+.2f}" for t in op]
    md += [f"- {t['sym']} {f(t['entry_ms'])} -> {f(t['exit_ms'])} {t['exit']} {t['usdt']:+.2f}" for t in cl[-30:]]
    (HERE / "PAPER_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def main() -> None:
    (HERE / "paper_pid.txt").write_text(str(os.getpid()), encoding="utf-8")
    s = json.loads(ST.read_text(encoding="utf-8")) if ST.exists() else {}
    while True:
        try:
            step(s)
            s["checked_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            ST.write_text(json.dumps(s, indent=1), encoding="utf-8")
            report(s)
        except Exception as e:  # noqa: BLE001 - keep polling
            log(f"ERROR {type(e).__name__}: {e}")
        due = time.time() + 60
        while time.time() < due:
            time.sleep(5)


if __name__ == "__main__":
    main()
