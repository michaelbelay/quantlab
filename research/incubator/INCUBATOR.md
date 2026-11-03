# Strategy incubator (built 2026-10-07, approved by Michael: "yes build it")

Michael's design point: no strategy wins every market, and a lab that only judges is a hospital. So discovery runs
continuously and freely; only promotion is strict, and promotion uses **new data only**.

```
 DISCOVERY (weekly agent + anyone)  ->  INCUBATOR (paper, many ideas at once)  ->  VERDICT (new data only)
 old development data, light check      forward from the hour it entered           🟡 promoted / 🔴 killed / ⚪ expired
```

## 1. Discovery: free
- An idea is one file in `ideas/` (format in `incubator.py` docstring): a rule (signals + side/hold/stop/market
  type) or a book of existing pipeline candidates per market type.
- Screen on development coins 2021-01..2026-09 (`incubator.py screen`). Light check: ≥ 200 trades, PF ≥ 1.10,
  PF at 2× costs ≥ 1.00, day-weighted t ≥ 2.0, positive in ≥ 4 years (years with ≥ 20 trades).
- **Every screen is logged as a trial** (`screens` table). The count is shown in every report, so the number of tries
  behind a promotion is never hidden.
- Only a file whose exact sha256 passed a screen can enter (`add`). Exception: `--manual "<reason>"`, for ideas that
  already have documented evidence (written in the reason).
- Discovery may use: development coin files, BTC daily, pipeline trade files, the scanner's live data.
  **Never**: the 280 unseen coins, the sealed desk quadrant, out-of-time 2017-20 data (those stay for pre-registered
  tests).

## 2. Incubation: paper, forward only
- When an idea enters, its file is frozen (sha256) and its forward start is the current hour. Only trades **entered
  after that hour** count.
- Daily, `evaluate` runs every incubating idea on the scanner's `live_cache` (top-200 Binance USDT perps, closed 1h
  candles + funding; same trade mechanics as `downtrend.py`: 0.2% costs, funding, stop on high/low). Trades still
  open at the end of the data do not count.
- If the idea file, `incubator.py` or `downtrend.py` changes after freezing (`code_hashes.txt`), the idea becomes
  ⛔ TAMPERED and no verdict is given until reviewed.
- Nothing is ever traded. No order, no bot.

## 3. Verdict (fixed, per idea; default 50 trades on 20 distinct entry days, 365-day limit)
- Once ≥ min trades **and** ≥ min days: day-weighted average ≤ 0 → 🔴 KILLED;
  day-weighted average > 0 **and** day t ≥ 2 **and** PF at 2× costs ≥ 1.00 → 🟡 PROMOTED.
  In between: keeps incubating.
- Still no verdict at the limit → ⚪ EXPIRED (too rare to judge).
- 🟡 means: 300 USDT simulation, then Michael decides. 🟢 / live only by Michael.
- A rule set is part of the frozen idea file (`RULE = {...}`) and cannot change after entry; a changed idea is a new
  file and starts again from zero.

## 4. Reports
- `state.json` after each evaluation; `REPORT_latest.md` weekly (also shown in the quantlab UI, Incubator tab).
- A Windows toast when an idea changes status.
- The 13 scanner rules keep their own forward log (`research/opportunity/forward.py`) and are listed in the report.

## Schedule
- `Quantlab Incubator Daily`: `incubator.py evaluate` then `report`, daily 03:30 local.
- `Quantlab Discovery Weekly`: headless Claude Code with `DISCOVERY_PROMPT.md`, Monday 09:00 local.

## First intake (2026-10-07, manual, evidence in the linked results)
| Idea | Why it is here |
|---|---|
| `flush_f1` | `FLUSH_RESULT_2026-10-07.md`: PF 2.54 in 2024-26 but 3 crash days carry it; needs new crash days |
| `switch_book` | `REGIME_SWITCH_RESULT_2026-10-07.md`: failed, but the switch beat always-on |
| `channel_uphivol` | same result: the one cell positive in the test window (post-hoc) |

## 2026-11-01 hash lock re-set
On 2026-10-31 all 8 ideas went TAMPERED because the data folders moved: incubator.py (BTC_1D path) and downtrend.py
(FUT/OOS/split_140 paths) changed by file paths only, logic byte-identical to the locked copies (checked by diff).
code_hashes.txt re-hashed, the 8 ideas set back to INCUBATING with their original forward start. Idea files unchanged.
