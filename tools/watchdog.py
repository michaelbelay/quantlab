r"""Watchdog for the paper bots: one pass = look at each bot, start the ones that are not running, write it down.

    .venv\Scripts\python.exe tools\watchdog.py --check     show the state, start nothing
    .venv\Scripts\python.exe tools\watchdog.py             one pass
    install_watchdog.bat                                   Windows runs a pass every 5 minutes (also after a reboot)

Why (2026-11-03): a reboot ended all three paper bots at the same minute and nothing started them again for 8 days.

"Running" is not guessed from a pid number:
  paper trader  - it holds a lock on data\trader\paper.lock for as long as it lives; if the lock can be taken, it is gone.
  switcher, delist - the pid in their pid file must be a live python process whose command line names their script.
A bot that is running but has not reported for a long time (PC asleep, Binance unreachable, a hang) is NOT restarted -
a second copy would not help - it is reported, at most once an hour.

Off switch: create the file data\watchdog_off.txt (delete it to switch on again). Never starts the LIVE trader.
Log: data\watchdog.log. Restarts and warnings also go to Telegram when it is set up.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from trader.fsio import age_min, write_atomic  # noqa: E402

PYW = ROOT / ".venv" / "Scripts" / "pythonw.exe"
DATA = ROOT / "data"
LOG, OFF, MEMO = DATA / "watchdog.log", DATA / "watchdog_off.txt", DATA / "watchdog_state.json"
FRESH = ROOT / "research" / "fresh"
RESTART_GAP_S = 180          # a bot the watchdog started is given this long before it is looked at again
WARN_GAP_S = 3600


def lock_free(path: Path) -> bool:
    """True if nobody holds the trader's lock (= no trader process)."""
    import msvcrt
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+") as fh:
        try:
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        return True


def pid_runs(pid_file: Path, script: str) -> bool:
    """True if the pid in the file is a live process whose command line contains `script`."""
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False
    try:
        import psutil
        return script.lower() in " ".join(psutil.Process(pid).cmdline()).lower()
    except ImportError:
        r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, timeout=15,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return str(pid) in r.stdout and "python" in r.stdout.lower()
    except Exception:  # noqa: BLE001 - psutil.NoSuchProcess / AccessDenied: not ours, or gone
        return False


def json_age_min(path: Path, key: str) -> float | None:
    """Minutes since the UTC time stored under `key` in a json file ('YYYY-MM-DD HH:MM:SS' or ISO)."""
    try:
        raw = str(json.loads(path.read_text(encoding="utf-8"))[key]).replace("T", " ")[:19]
        t = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return round((datetime.now(timezone.utc) - t).total_seconds() / 60, 1)
    except Exception:  # noqa: BLE001
        return None


BOTS = [
    {"name": "paper trader", "cmd": ["-m", "trader", "run", "paper"],
     "running": lambda: not lock_free(DATA / "trader" / "paper.lock"),
     "age": lambda: age_min(DATA / "trader" / "paper_heartbeat.txt"), "late_min": 15},
    {"name": "switcher paper", "cmd": ["-u", r"research\fresh\switcher_paper\paper.py"],
     "running": lambda: pid_runs(FRESH / "switcher_paper" / "pid.txt", r"switcher_paper\paper.py"),
     "age": lambda: json_age_min(FRESH / "switcher_paper" / "status.json", "checked_utc"), "late_min": 130},
    {"name": "delist paper", "cmd": ["-u", r"research\fresh\delist\paper.py"],
     "running": lambda: pid_runs(FRESH / "delist" / "paper_pid.txt", r"delist\paper.py"),
     "age": lambda: json_age_min(FRESH / "delist" / "paper_state.json", "checked_utc"), "late_min": 30},
]


def say(msg: str, alert: bool = False) -> None:
    line = f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC - {msg}"
    print(line, flush=True)
    DATA.mkdir(exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    if alert:
        try:
            from trader import notify
            notify.send("[watchdog] " + msg)
        except Exception:  # noqa: BLE001 - the log line is enough
            pass


def start(cmd: list[str]) -> int:
    """Start a bot with no window, cut loose from this process (and from the scheduled task that ran us)."""
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    kw = dict(cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
    try:
        return subprocess.Popen([str(PYW), *cmd], creationflags=flags | 0x01000000, **kw).pid     # CREATE_BREAKAWAY_FROM_JOB
    except OSError:                                                                             # job forbids breakaway
        return subprocess.Popen([str(PYW), *cmd], creationflags=flags, **kw).pid


def main(check: bool = False) -> int:
    if OFF.exists() and not check:
        return 0
    try:
        memo = json.loads(MEMO.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        memo = {}
    now, down = time.time(), 0
    for b in BOTS:
        name, m = b["name"], memo.setdefault(b["name"], {})
        running, age = b["running"](), b["age"]()
        if check:
            print(f"{name:<15} {'running' if running else 'NOT RUNNING':<12} last report {age if age is not None else '?'} min ago")
            down += not running
            continue
        if running:
            if age is not None and age > b["late_min"] and now - m.get("warned", 0) > WARN_GAP_S:
                m["warned"] = now
                say(f"{name} is running but has not reported for {age:.0f} min (PC asleep? no internet? hung?)", alert=True)
            continue
        if now - m.get("started", 0) < RESTART_GAP_S:
            continue
        m["started"], m["restarts"] = now, m.get("restarts", 0) + 1
        try:
            pid = start(b["cmd"])
            say(f"{name} was not running - started it (pid {pid}, restart no. {m['restarts']})", alert=True)
        except Exception as e:  # noqa: BLE001
            say(f"{name} was not running and could NOT be started: {type(e).__name__}: {e}", alert=True)
    if check:
        print("watchdog is", "OFF (data\\watchdog_off.txt exists)" if OFF.exists() else "on")
        return 1 if down else 0
    write_atomic(MEMO, json.dumps(memo))
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
