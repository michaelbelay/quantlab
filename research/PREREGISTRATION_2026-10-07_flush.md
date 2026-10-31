# Pre-registration: flush bounce in falling markets, 2026-10-07

Approved: Michael, 2026-10-07 ("ok"). Written before any rule below was run on 2024-26 data or on the unseen coins.
This text and `research/flush.py` are hashed into `research/flush/hashes.txt` before the first run.

## Where the idea comes from (stated honestly)
From the downtrend run (`DOWNTREND_RESULT_2026-10-07.md`, fit window 2021-23 only): in BTC-downtrend days, shorting
after a volume breakdown (t −5.1) and shorting very negative funding (t −2.6) lost strongly, and buying a capitulation
for 24h was the best rule (PF 1.69, t 1.5). Hypothesis: **in a falling market, after a violent flush with crowded
shorts, price bounces within about one day.** It was found by looking at 2021-23, so 2021-23 cannot confirm it.
The decision is made only on data that run did not touch: 2024-26 on the development coins (test A), then the 280
unseen coins (test B).

## Rules (3, fixed; mechanics exactly as in `downtrend.py`, unchanged)
All: enter only on a BTC `DN` day (BTC daily close below its 50-day average, known at the previous close); signal at a
1h bar's close, entry next bar open; **long, hold 24h, stop 1.5σ** (σ = coin's 20-day std of 24h returns); costs 0.2%
round trip + funding; one open trade per coin per rule.

| ID | Flush signal | Same signal as |
|---|---|---|
| F1 | 24h return ≤ −2.5σ and 24h volume ≥ 3× its 30-day average (first bar of the condition) | D4a, unchanged |
| F2 | close crosses below the lowest low of the previous 480 bars and 24h volume ≥ 2× its 30-day average | D3b signal, opposite side, 24h hold |
| F3 | last funding < 0 and in the bottom 5% of its last 90 days (first bar of the condition) | D5a signal, opposite side |

3 trials (the 12 of the downtrend run and 1136 of the regime-switch run are recorded as related).

## Information only (no decision)
Fit-window numbers for F1-F3 (2021-23, development coins, DN days) and the same rules on UP days, reported next to
the test results.

## Test A: development coins, entries 2024-01-01 .. 2026-09-18, DN days
A rule passes if **all** hold:
- A1 PF ≥ 1.10 and PF ≥ 1.00 with an extra 0.2 per trade (2× costs);
- A2 day-weighted t ≥ 2.0 (trades of one entry day averaged first);
- A3 positive in ≥ 2 of 3 periods (2024, 2025, 2026-01..09);
- A4 above the 95th percentile of 1000 random replicas (same number of long trades per entry day, random coins and
  hours of that day, same hold and stop): the flush has to beat simply buying on the same days.
- A5 ≥ 100 trades.

## Test B: 280 unseen coins (on-purpose use, pre-registered here), entries 2024-01-01 .. 2026-08-31
Only rules that pass A. Same checks A1-A5.

## Decision
| Result | Class | Next |
|---|---|---|
| fails A | 🔴 | recorded; the flush-bounce idea is closed for these signals |
| passes A, fails B | 🟠 | recorded; no forward test |
| passes A and B | 🟡 | 300 USDT simulation (`research/cap300/sim.py`, DD ≤ 40%), then a paper forward test, and it fills the DN slot of the switching book. 🟢 never before the forward test |

No re-run with other holds, stops, thresholds or market definitions after the result is seen.

## Data rules
Development coin futures files, BTC daily file, the 280 unseen coins only in test B. Not read: the sealed desk
quadrant, out-of-time 2017-20 data.
