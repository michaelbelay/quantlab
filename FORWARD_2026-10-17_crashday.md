# Crash-day forward log (Bear-Wild) — registered 2026-10-17, before any forward data

Michael 2026-10-17: "Build the crash-day forward log (Bear-Wild): fixed rule for what a crash day is, log BTC/ETH +
the flush setup going forward, fixed verdict at N events. Register first, then let it run. This closes the empty cell."

Purpose: the Bear-Wild cell of the strategy library (`catalog.json`) has nothing tested. This log measures, on new
data only, what happens on crash days in that cell, and answers with one of: a bounce long, a continuation short, the
flush setup, or **cash** (none of them pays). Paper only: nothing is ever ordered. Nothing here was fitted on outcomes;
the only historical number looked at before writing this was how often a crash day happens (frequency, below).

## 1. What a crash day is (fixed)
Data: Binance USD-M BTCUSDT perp, daily candles (00:00 UTC). Day D is known when it closes (D+1 00:00 UTC).
- **Crash day**: BTC daily return r_D = close_D / close_D-1 − 1 is **≤ −2 × σ20 AND ≤ −4%**, where σ20 = standard
  deviation of the 20 daily returns *before* D.
- **Cell at D's close** = the Today-tab / VBreak4BullCalm rule including day D (`bullcalm_rule.market_condition` at
  D+1 00:00): Bear = BTC 20-day return ≤ 0; Wild = BTC 20-day volatility > its median over the previous 365 days.
- **Event** = a crash day whose cell is **Bear-Wild**. Crash days in other cells are logged as context, not judged.
- **Clusters**: a crash day within 2 days of the previous event's day (D ≤ previous + 2) is logged but is the same event
  (no new trades). One event = one independent observation.

Frequency 2021-01 → 2026-10 (BTC 1d futures file, the only history looked at): 23 Bear-Wild crash days = 22 events,
4.5 a year (2021 1, 2022 5, 2023 1, 2024 5, 2025 6, 2026 4). All cells: 57 crash days, 11.7 a year.

## 2. What is logged for every event (fixed)
Entry for all BTC/ETH legs = the D+1 00:00 UTC 1h open. Costs 0.10% per side + real funding. σ24 = std of the last 720
1h log returns × √24 (same as the V4 forward test).
- **L — bounce long**: long BTC and long ETH, exit at the close of the 72nd 1h bar, stop entry × (1 − 3 σ24).
- **S — continuation short**: short BTC and short ETH, exit at the close of the 72nd 1h bar, stop entry × (1 + 3 σ24).
- Event result for L and S = average of the BTC and ETH legs (net %).
- Descriptive only (not judged): BTC and ETH raw returns from the entry at +24 h, +72 h, +7 days.
- **F — flush setup**: trades of the frozen incubator idea `research/incubator/ideas/flush_f1.py` (F1 crash bounce: coin
  down ≥ 2.5 σ in 24 h on ≥ 3× normal volume → long next hour, stop 1.5 σ, exit 24 h, only on DN days), computed with
  the incubator's own code (`incubator.rule_trades`, `downtrend.load_coin`) on the scanner's live_cache (top-200 Binance
  USDT perps), whose **signal bar falls on day D or D+1**. Event result for F = average of that event's flush trades.
  An event with no flush trade counts for L/S but not for F.

## 3. Verdict (fixed now)
Look at **10 events** (Bear-Wild clusters), or **2028-10-17**, whichever comes first. At 5 events: a descriptive look
only, no verdict.
For each of L, S, F separately:
- **🟡 passes** if: average event result > 0 AND PF over events ≥ 1.3 AND ≥ 60% of events positive
  (F also needs ≥ 30 flush trades in total).
- **🔴 fails** otherwise.
Cell answer: the passing setup(s) are offered to Michael for the Bear-Wild cell (he decides about a paper bot or live
profile; nothing is switched on automatically). If none passes, the cell is closed as **"Cash on crash days"**
(measured, not assumed).
Fewer than 5 events on 2028-10-17 → too rare to judge; Michael decides whether to continue.
The rule and the code do not change during the test. A changed rule is a new test from zero (counted as new trials:
this log adds 3 — L, S, F).

## 4. Code and running
- `C:\quantlab\research\fresh\forward_crash\crash_forward.py` (old-bot
  venv): rebuilds the BTC/ETH record from public Binance data every run (missed runs lose nothing); freezes each event's
  flush trades into `events.json` once its window is closed (live_cache keeps ~200 days, so a late run still finds them).
  Writes `state.json`, `events.json`, `run.log`.
- Windows task `Quantlab Crashday Forward`: hourly, pythonw (no window).
- Forward start: first day that can be a crash day = **2026-10-18** (decided at 2026-10-19 00:00 UTC). Nothing before
  counts.

## Erratum + checks (2026-10-17, after registration; rule unchanged)
- Frequency note in section 1 undercounted 2021: the 1d file used starts 2021-01-01, so the 365-day volatility median
  did not exist for most of 2021. With full history (Binance 1d from 2019-11): **27 Bear-Wild crash days = 26 events
  2021-01 → 2026-10, 4.5 a year** (2021 5, 2022 5, 2023 1, 2024 5, 2025 6, 2026 4). Verdict size (10) unchanged.
- Flush code check: the sliced live_cache load gives identical trades to the incubator's full load on 2026-06-02 and
  2026-06-05 (2/2 and 5/5 trades, same coins, times and P&L). Full 366-coin run: 33 s.
- Historical replay (`crash_forward.py --replay 2021-01-01`, **reference only, not part of the verdict**, looked at
  after this file was committed): L bounce long 26 events avg +0.51%, PF 1.19, 50% positive (would fail);
  S continuation short avg −2.25%, PF 0.47 (would fail). F not replayable (live_cache starts 2026-03-31); 2026-06-05
  alone: 5 flush trades.
