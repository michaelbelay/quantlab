r"""Start the UI server with no window (2026-10-14, Michael: no pop-ups, everything in the background).

start_ui.bat calls:  .venv\Scripts\pythonw.exe ui\launch_hidden.pyw
The server runs under python.exe with CREATE_NO_WINDOW (a hidden console its children inherit) and logs to
data\ui_server.log. This launcher exits right away; the server keeps running.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    log = open(ROOT / "data" / "ui_server.log", "a", encoding="utf-8")
    subprocess.Popen([str(ROOT / ".venv" / "Scripts" / "python.exe"), "-u", str(ROOT / "ui" / "server.py")],
                     cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                     creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
