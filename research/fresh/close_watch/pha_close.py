"""One-off (Michael 2026-10-26): force-exit the NFI PHA trade when PHAUSDT last price >= 0.056. Stops after closing,
or when the trade is no longer open."""
import base64, json, sys, time, urllib.request
from datetime import datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import live_control as L  # noqa: E402
HERE, TARGET, PAIR = Path(__file__).resolve().parent, 0.056, "PHA/USDT:USDT"


def log(m):
    with (HERE / "pha_close_log.txt").open("a", encoding="utf-8") as fh:
        fh.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} - {m}\n")


def forceexit(tid):
    a = json.loads(L.CONFIG.read_text(encoding="utf-8"))["api_server"]
    tok = base64.b64encode(f"{a['username']}:{a['password']}".encode()).decode()
    req = urllib.request.Request(f"http://127.0.0.1:{a['listen_port']}/api/v1/forceexit", method="POST",
                                 headers={"Authorization": f"Basic {tok}", "Content-Type": "application/json"},
                                 data=json.dumps({"tradeid": str(tid), "ordertype": "market"}).encode())
    return urllib.request.urlopen(req, timeout=20).read().decode()


(HERE / "pha_close_pid.txt").write_text(str(__import__("os").getpid()))
log(f"start: close {PAIR} at >= {TARGET}")
n = 0
while True:
    try:
        t = [x for x in L.bot_api("/status") if x["pair"] == PAIR]
        if not t:
            log("PHA trade no longer open - stopping"); break
        px = float(json.loads(urllib.request.urlopen("https://fapi.binance.com/fapi/v1/ticker/price?symbol=PHAUSDT", timeout=15).read())["price"])
        if px >= TARGET:
            log(f"price {px} >= {TARGET}: {forceexit(t[0]['trade_id'])}"); break
        n += 1
        if n % 60 == 1:
            log(f"price {px}, pnl {t[0]['profit_abs']:+.2f}")
    except Exception as e:  # noqa: BLE001
        log(f"ERROR {type(e).__name__}: {e}")
    due = time.time() + 20
    while time.time() < due:
        time.sleep(5)
