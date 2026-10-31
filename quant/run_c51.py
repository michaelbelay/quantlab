r"""C51 crowd surge on 222 non-meme coins (FAMILIES_C.md "C51", registered 2026-10-20 before this file existed).

    .venv\Scripts\python.exe -m quant.run_c51 fetch    # download 1h klines + funding (8 threads, cached in data/c51)
    .venv\Scripts\python.exe -m quant.run_c51 dev
    .venv\Scripts\python.exe -m quant.run_c51 valid    # refused without a recorded DEV pass

The C50 rule and code unchanged (run_c48 with the C50 settings); only the coin list and the data (native 1h klines).
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor

from . import run_c49
from . import run_c50  # noqa: F401 - C50 settings
from . import run_c48 as m
from .paths import DATA, RUNS

m.FAM = "C51"
m.COINS = json.loads((RUNS / "c51_coins.json").read_text(encoding="utf-8"))["coins"]
m.KURL = "https://data.binance.vision/data/futures/um/monthly/klines/{s}/1h/{s}-1h-{m}.zip"
m.CACHE = DATA / "c51"
m.OUT = RUNS / "c_trades" / "C51" / "1h"
m.fetch = run_c49._fetch15            # the plain downloader (reads KURL / CACHE at call time) - native 1h, no resampling

if __name__ == "__main__":
    if sys.argv[1:] == ["fetch"]:
        def one(c):
            d, f = m.fetch(c)
            return c, len(d), len(f)
        with ThreadPoolExecutor(8) as ex:
            for i, (c, nb, nf) in enumerate(ex.map(one, m.COINS), 1):
                print(f"{i}/{len(m.COINS)} {c}: {nb} bars, {nf} funding", flush=True)
        sys.exit(0)
    sys.exit(m.main())
