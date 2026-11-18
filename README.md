# quantlab

Crypto strategy research lab and trader for Binance USDT-M futures.

| Folder | What |
|---|---|
| `trader/` | Own trading engine (ccxt): FlowTrend signals, paper and live brokers, sqlite store, DPAPI key vault, Telegram |
| `ui/` | Local terminal UI on http://localhost:8500 (`start_ui.bat`) |
| `quant/` | Backtest and evaluation toolkit (families, walk-forward, trial counting) |
| `research/` | Registered studies, forward tests, scanner, incubator |
| `strategies/` | Strategy family definitions |
| `tests/` | Unit tests |

Data (`data/`), results (`runs/`), secrets (`secrets/`) and databases stay local and are not in this repository.

## Run

```
.venv\Scripts\python.exe -m trader run paper      # paper trading, no keys
.venv\Scripts\python.exe -m trader status paper
start_paper_bots.bat                              # paper trader + switcher + delisting paper bots
start_ui.bat
restart_trader_paper.bat                          # after a change in trader\: stop, start, show status
install_watchdog.bat                              # once: Windows restarts dead paper bots every 5 minutes
.venv\Scripts\python.exe -m pytest                # 36 tests, 17 of them on the trader's order path (no network)
```

Live trading needs a key saved with `python -m trader.vault set binance` (withdrawals off, IP-locked).
