# quantlab — technical assessment, 2026-11-07

Scope: whole repo as it stands (`main` @ a34a480), read-only inspection + test run + live probes.
Nothing was changed except adding this file.

## 1. What it is, in numbers

| | |
|---|---|
| Code | 3,966 lines `quant/` (29 files), 743 `trader/` (11), 1,296 `ui/` (6) + 2,687 frontend, 757 `strategies/` (3) |
| Tests | 19, all in `quant/` (sim, book, trades, twins, walk-forward) |
| Data | ~6.5 GB under `data/` (market 5.9 GB; old batch artefacts c47/c51/ext ~1 GB) |
| Research | 104 Protocol C ledger rows, 8,708 counted trials project-wide, 11 scheduled research tasks |
| Live | 3 paper bots (FlowTrend, Switcher, Delist), 1 UI server, no live account activity |

## 2. Headline verdict

| Layer | Grade | One line |
|---|---|---|
| Research method | **A−** | Pre-registration, hash-locked ideas, ledger, walk-forward now enforced, 2,000-rep twin tests, explicit "known deviations". Genuinely better than most retail quant work. |
| Research results | **D** | 99 of 104 Protocol C evaluations fail DEV; 0 families pass VALID; the project's own protocol has produced no tradeable strategy. |
| Paper/live operations | **F** | Everything manual died on 2026-11-03 ~14:00 and did not come back. A position is sitting **past its stop**; the Trader tab has been returning 502 for four days. |
| Execution code | **C** | Small, readable, sensible separation — but the live path is unexercised, unreconciled, has no kill switch, and its paper twin doesn't model the costs the research charges. |
| Engineering hygiene | **C−** | No pinned dependencies, no CI, no lint/type config, 3 git commits, runtime state files tracked in git, highest-risk code (trader/) has zero tests. |

## 3. What is genuinely good

1. **Adversarial discipline is real, not decorative.** Notable specifics:
   - `RULES.md` "Written vs executed — known deviations" openly records that the FINAL window is spent and that
     "no result may call [holdout coins] one" — most projects quietly keep reusing burnt data.
   - `PROTOCOL_C.md` implementation notes admit that the WALK-FORWARD gate was documented but *not enforced* until
     2026-10-09, and that the "2x/3x reported" promise had no code path until then. That is unusual honesty.
   - `quant/trials.py` de-duplicates near-identical families and estimates N_eff via the participation ratio,
     plus expected-max-t of pure noise. This is the correct response to 8,000+ trials.
   - Twins raised from 100 → 2,000 reps once noise near the p95 gate was understood.
2. **Failures are diagnosed and turned into mutations** (F1 → F3 → F4 → F5 chain is a model of how to iterate).
3. **Code is clean and small.** No bare `except:`, no TODO/FIXME/HACK, consistent docstrings, pandas/numpy used
   plainly, one module per idea.
4. **UI server security is better than expected**: loopback-only on both `::1` and `127.0.0.1`, POST endpoints
   guarded by Origin + `X-Quantlab` header (blocks cross-site writes without CORS), read-only by design.
5. **Secrets**: DPAPI vault, `secrets/`, `data/`, `runs/` git-ignored, no secret-like file ever tracked.

## 4. P0 — broken right now

### 4.1 The paper trader is dead and left a position past its stop
Evidence:
- `data/trader/paper.log` last tick **2026-11-03 13:00**; `paper_heartbeat.txt` mtime **14:00:09**.
- `data/trader/paper_state.json` still says `"state": "running"` — misleading.
- The switcher and delist paper bots also stop at **13:06 / 14:00** on the same day. Three independent manual
  processes dying at the same minute = machine crash or reboot, not a code exception.
- `paper_heartbeat.txt` contains **19 NUL bytes** (`00 × 19`) — exactly the length of a timestamp, i.e. a torn
  write during the crash. The heartbeat file is not written atomically.
- Current open trades (`python -m trader status paper`):

| coin | side | entry | stop | now | P&L | opened | problem |
|---|---|---|---|---|---|---|---|
| HYPE | long | 88.063 | 81.716 | 78.554 | **−7.22** | 11-01 14:45 | **stop breached**, no exit |
| NEAR | short | 4.102 | 4.623 | 3.700 | +6.48 | 11-02 13:00 | past 48 h time exit |

Neither `stop` nor `time_48h` fired because nothing was running. The paper forward-test record now has a 4-day hole
and its book does not reflect the strategy's own rules. Live would have been protected by the exchange stop, but the
time exit and the record would still be wrong.

### 4.2 The Trader tab has been 502 for four days
`ui/trader_view._age_min()` does `datetime.strptime(beat.strip(), …)` with no validation. The NUL-filled heartbeat
raises `ValueError`, `/api/trader` returns 502. Confirmed against the running server:

```
{"error": "ValueError: time data '\x00...\x00' does not match format '%Y-%m-%d %H:%M:%S'"}
```

So the one screen that would have shown "the bot is dead" is itself broken.

### 4.3 No watchdog
`start_paper_bots.bat` / `start_trader_paper.bat` fire once. There is no scheduled task, service, or heartbeat
monitor for the trader (the 11 scheduled tasks cover research only). Any reboot silently ends paper trading.

### 4.4 Two UI servers, one stale
PIDs 23360 and 22476 both run `ui\server.py`; only 22476 holds :8500. A second process is leaked on every
`start_ui.bat` failure path. Harmless today, confusing when debugging.

## 5. Research state — what the numbers actually say

| Measure | Value |
|---|---|
| Protocol C evaluations | 104 (99 FAIL DEV, 1 PASS DEV, 3 FAIL VALID, 1 off-protocol "PASS") |
| Families passing VALID | **0** |
| Best DEV PF (1h) | C50 1.47 (103 trades → under the 200-trade gate), C32 1.16 (1,631 trades, then FAIL VALID) |
| Trial count | 8,708 raw / 8,651 unique (315 quantlab C+F unique + 295 pipeline + 8,000 legacy offset + 50 screens) |
| Expected best t of pure noise | see `runs/trials.json` → `expected_best_t_of_noise` |

Interpretation: the lab has not found an edge, and it knows it. That is a legitimate outcome, but it is worth stating
plainly because the UI tells a different story.

### 5.1 `catalog.json` contradicts the ledger
`catalog.json` (What Works tab, last edited 2026-10-17) shows:
- **MajorsTrend — green, "Passed on never-used data (2017-2020)", 300 → 5,732, worst drop 38%.**
- **VBreak4Live — yellow, "passes in Bull + Calm only", PF 1.55.**

Both come from the legacy bot and sit outside the Protocol C / RULES gates. The ledger says nothing passed. A reader
of the UI will believe a green strategy exists. Either label these as "legacy evidence, not validated under current
protocol", or put them through the current gates.

### 5.2 The one "PASS" in the ledger deserves suspicion, not celebration
`E1` (5m, 2026-10-20): 582 trades, PF 1.72, win rate 75.6 %, avg +0.93 %/trade, 300 → 407–782 per month, worst trade
−25 %. Against the scalp lab's 0/6 pass rate on the same idea space, that profile is more likely a look-ahead or
data-alignment bug (5m bar timestamps / funding alignment) than a genuine scalping edge. It also passed a bespoke
"check" outside `PROTOCOL_C`. Reproduce it from scratch on held-out coins before anyone builds on it.

## 6. Execution engine — concrete risks

Ranked by what would cost money:

1. **Orphan position on live** (`trader/engine.py:110-117`, `broker.py:74-88`): the entry is sent, then the stop is
   sent, then the row is written. If `create_order` (stop) throws, the exception bubbles to the tick loop — the
   exchange position exists **with no stop and no DB row**, and will never be managed. No try/except, no emergency close.
2. **No startup reconciliation**: nothing compares open DB trades to exchange positions on start. The only handling is
   `LiveBroker.stopped()`, which assumes "position gone = stop filled" and will attribute a manual close or a
   liquidation to a stop. Large fill price errors are possible.
3. **No kill switch**: no max daily loss, no max drawdown halt, no per-coin notional cap, no "stop trading after N
   consecutive errors". `errors` is counted but only used for Telegram messages.
4. **Paper engine ≠ research costs** (`broker.py:27-35`): no funding, no slippage, entry at `last` price rather than
   the next bar open, stops evaluated by 20 s polling of `last` instead of intrabar high/low. Research charges
   0.05 % slippage per side + real funding. The forward test will therefore look better than the backtest for
   reasons that have nothing to do with the strategy.
5. **The trader ignores its own regime evidence.** `research/fresh/regime_now.json` / the old-bot stats show FlowTrend
   at **−1.33 %/trade, 35 % win rate in "down"** regimes, +3.26 %/trade only in "up / calm". The live trader has no
   regime gate at all. Current label (2026-11-06): sideways / normal / weak breadth.
6. **`vault.py` passes the API secret through a PowerShell `-Command` string** (`encrypt`). It is transient, but it can
   land in process command lines and PowerShell script-block logging. Low probability, high blast radius; DPAPI via
   `ProtectedData` in-process would remove it.

## 7. Engineering hygiene

| Gap | Detail |
|---|---|
| Dependency pinning | **No `requirements.txt`, `pyproject.toml`, `setup.cfg`, lock file.** The only record of the environment is the `.venv` folder. Not reproducible on another machine or after a rebuild. |
| CI | None. `pytest` is run by hand. |
| Lint/types | None configured (no ruff/flake8/mypy). Code is clean enough that this is cheap to add. |
| Test coverage | 19 tests, all `quant/`. **0 tests for `trader/`** (order lifecycle, stop handling, restart, store, engine), **0 for `ui/`**, **0 for `strategies/`**. The riskiest and least-tested code is the money path. |
| Git | 3 commits total (2026-10-31 → 11-03), ~7 MB. Working tree is full of modified runtime files (`research/**/state.json`, `REPORT_latest.md`, `ui/server.py`, `app.js`). `git status` is unusable as a signal; two commits are bulk "everything" imports. |
| Dead weight | `quant/run_c42_c43.py` is 574 lines; ~12 one-off `run_cNN.py` scripts duplicate loading/printing. Old batch artefacts (~1 GB) have no retention policy. |
| Portability | `msvcrt` file locking and DPAPI = Windows-only by design. Fine, but it means no Linux/VPS deployment without work — relevant given the "Tokyo server" question in `REGISTER_SCALP_2026-10-29.md`. |
| Perf | `python -m quant.trials` did not finish in 120 s (reads every c_trades parquet). Move to a cached summary. |

## 8. What I would do, in order

### Today
1. **Close the book deliberately.** Restart `python -m trader run paper` (it will exit NEAR on `time_48h` and HYPE on
   the crossed stop in the first tick), or close both rows by hand. Then write the 2026-11-03 → 11-07 gap into the
   forward-test log so the record stays honest.
2. **Fix the heartbeat and the Trader tab.** Write the heartbeat atomically (`tmp` + `os.replace`), and make
   `_age_min` return `None` on parse failure instead of raising. One-line fix, unblocks the only monitoring screen.
3. **Add a watchdog**: a scheduled task every 5 min that starts the paper trader if `heartbeat age > 5 min`, and logs
   every restart. Same for switcher/delist if they are meant to keep running.
4. Kill the stale second UI server (PID 23360).

### This week
5. Put the 2 stale trades' outcome into `research/fresh/*/` state files; do not let an unmanaged window count as
   strategy performance.
6. Make the paper broker cost-faithful (funding + slippage + next-open entry + intrabar stop). Without this the forward
   test cannot confirm or refute a backtest.
7. Write `tests/test_trader.py` against a fake broker: entry → stop → time exit; restart with open trade; stop order
   fails; store round-trip. This is ~100 lines and covers the money path.
8. `pip freeze > requirements.txt` (then hand-trim), add `pyproject.toml` with pytest + ruff, and a GitHub Actions
   workflow that runs `pytest -q` on push.
9. Add `.gitignore` entries for `research/**/state.json`, `research/**/REPORT_latest.md`, `research/**/*_log.txt`,
   `data/**`; commit code and registers only.

### This month
10. **Falsify or confirm E1.** Re-run the 5m check on held-out coins with a strict bar-timestamp audit; if it
    survives, register it properly under Protocol C. If not, record it as a data bug.
11. **Reconcile the UI with the research.** Either put MajorsTrend/VBreak4 through the current gates, or relabel them
    "legacy, not validated".
12. **Decide the research strategy.** 104 Protocol C evaluations, 0 validated. Broad screening is no longer buying
    information at an acceptable rate. Either (a) stop screening and push one mechanism (funding/carry is the only one
    with repeatedly positive raw evidence) through a full forward test, or (b) accept the lab's value is measurement,
    not alpha, and stop implying otherwise in the UI.
13. Add the missing live-path safety before any real money: reconciliation on start, stop-failure emergency close,
    daily-loss kill switch, and a hard position-count check against the exchange.

## 9. Bottom line

The research half of this project is disciplined enough to be trusted: it registers before it looks, counts its
trials, de-duplicates its families, escalates twin tests, and documents its own burnt data. That is rare.

The execution half is not yet at the same standard. A machine event on 2026-11-03 killed every manual paper bot, left
a position past its stop, corrupted the heartbeat, and took the monitoring tab down — and nothing noticed for four
days. No number produced by the paper book since 11-03 should be trusted, and none of the live code has ever been
exercised against a real account.

So: the lab is honest, the results are empty, and the plumbing is the thing to fix next.
