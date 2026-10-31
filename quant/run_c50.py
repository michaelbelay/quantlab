r"""C50 Meme crowd impulse 1h, strong surges only (FAMILIES_C.md "C50", registered 2026-10-20 before this file existed).

    .venv\Scripts\python.exe -m quant.run_c50 dev
    .venv\Scripts\python.exe -m quant.run_c50 valid    # refused without a recorded DEV pass

C49 unchanged except volume and number of trades must both be >= 6x their previous-24-bar means (C49: 3x).
"""
from __future__ import annotations

import sys

from . import run_c49  # noqa: F401 - applies the 1h setup to run_c48
from . import run_c48 as m
from .paths import RUNS

m.FAM, m.MULT = "C50", 6.0
m.OUT = RUNS / "c_trades" / "C50" / "1h"

if __name__ == "__main__":
    sys.exit(m.main())
