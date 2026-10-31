"""Run a console command with no window (2026-10-13, Michael: PowerShell windows popping up are annoying).

Scheduled tasks call:  .venv\\Scripts\\pythonw.exe hidden_run.pyw <program> [args...]
pythonw has no console; the child gets a console without a window (CREATE_NO_WINDOW), which its own children
inherit, so nothing flashes. Waits for the child and returns its exit code, so the task's Last Result stays real.
"""
import subprocess
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(2)
    sys.exit(subprocess.run(sys.argv[1:], creationflags=subprocess.CREATE_NO_WINDOW).returncode)
