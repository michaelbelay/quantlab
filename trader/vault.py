"""Secrets encrypted with Windows DPAPI (only this Windows user on this PC can read them). Values are never printed.

    .venv\\Scripts\\python.exe -m trader.vault set binance      # asks for key + secret (hidden typing)
    .venv\\Scripts\\python.exe -m trader.vault list
"""
from __future__ import annotations

import getpass
import json
import os
import subprocess
import sys
from pathlib import Path

from .settings import SECRETS

_PS = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0"


def _ps(script: str, stdin: str | None = None) -> str:
    env = os.environ.copy()
    env["PSModulePath"] = str(_PS / "Modules")          # Windows PowerShell 5.1 modules, whatever shell started us
    r = subprocess.run([str(_PS / "powershell.exe"), "-NoProfile", "-NonInteractive", "-Command", script],
                       input=stdin, capture_output=True, text=True, timeout=60, env=env,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode != 0:
        raise RuntimeError("DPAPI call failed")
    return r.stdout.strip()


def encrypt(plain: str) -> str:
    """The secret is handed to PowerShell on its input, not inside the command: a command line can be read by other
    programs of this user and can end up in PowerShell's logs. (Keys and tokens are plain ASCII; anything else
    takes the old route, because the input pipe's code page is not reliable for other characters.)"""
    if plain.isascii() and "\n" not in plain and "\r" not in plain:
        return _ps("ConvertFrom-SecureString (ConvertTo-SecureString ([Console]::In.ReadLine()) -AsPlainText -Force)",
                   stdin=plain + "\n")
    esc = plain.replace("'", "''")
    return _ps(f"ConvertFrom-SecureString (ConvertTo-SecureString '{esc}' -AsPlainText -Force)")


def decrypt(blob: str) -> str:
    return _ps(f"$s = ConvertTo-SecureString '{blob}'; "
               "[Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))")


def _file(name: str) -> Path:
    return SECRETS / f"{name}.json"


def get(name: str) -> dict | None:
    """Decrypted fields of a saved secret, or None if it doesn't exist."""
    p = _file(name)
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    out = {k: v for k, v in d.items() if not k.endswith("_enc")}
    out.update({k[:-4]: decrypt(v) for k, v in d.items() if k.endswith("_enc")})
    return out


def put(name: str, plain: dict, public: dict | None = None) -> None:
    SECRETS.mkdir(parents=True, exist_ok=True)
    enc = {k: encrypt(v) for k, v in plain.items()}
    for k, v in plain.items():                          # read every value back before anything is written
        if not enc[k] or decrypt(enc[k]) != v:
            raise RuntimeError(f"'{k}' did not survive encryption - nothing was saved, the old file is unchanged")
    d = dict(public or {}) | {f"{k}_enc": v for k, v in enc.items()}
    _file(name).write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    if argv[:1] == ["list"]:
        for p in sorted(SECRETS.glob("*.json")):
            print(p.stem, sorted(json.loads(p.read_text()).keys()))
        return 0
    if argv[:2] == ["set", "binance"]:
        key = getpass.getpass("Binance API key (hidden): ").strip()
        sec = getpass.getpass("Binance API secret (hidden): ").strip()
        put("binance", {"key": key, "secret": sec}, {"hint": key[-4:]})
        print("saved, key ending", key[-4:])
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
