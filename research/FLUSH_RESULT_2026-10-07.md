# Result: flush bounce in falling markets, 2026-10-07 — 🔴 (all 3 fail test A; test B not run)

Rules: `PREREGISTRATION_2026-10-07_flush.md`; hashes `flush/hashes.txt` (frozen before the run); script `flush.py`
(mechanics from `downtrend.py`); numbers `flush/testA.json`, trades `flush/testA_F*.parquet`.
Test A = 133 development coins, entries 2024-01-01..2026-09-18 on BTC-downtrend days, long 24h, stop 1.5σ, 0.2%
costs + funding.

| Rule | Trades | Days | PF | PF 2× | Day t | 2024 / 2025 / 2026 | vs random | Verdict |
|---|---|---|---|---|---|---|---|---|
| F1 capitulation (24h ≤ −2.5σ, volume ≥ 3×) | 426 | 101 | **2.54** | 2.42 | **1.02** ✗ | +513 / +1056 / +231 | p100 | fail A2 |
| F2 volume breakdown below 20-day low | 577 | 92 | 1.06 ✗ | 1.01 | 0.90 ✗ | +375 / +64 / −308 | p99.9 | fail A1, A2 |
| F3 very negative funding | 7226 | 439 | 0.97 ✗ | 0.88 | 1.09 ✗ | +507 / −894 / −98 | p99.3 | fail A1, A2, A3 |

Information: fit 2021-23 F1 PF 1.69 / F2 1.20 / F3 1.15 (all t < 1.6). Same rules on UP days in the test window:
F1 PF 1.33, F2 1.00, F3 1.01.

**Verdict 🔴** by the frozen rules. No re-run with other settings.

## Why F1 fails although its PF is 2.5 (checked after the verdict, information only)
- Its +1800 comes from **3 market-wide crash days**: 2025-02-03 (+808, 59 trades), 2026-02-06 (+388, 45 trades), and
  2024-08-05 (+281, 84 trades). Those 3 days are 82% of the profit. Without them: +324 over 98 days.
- Median day ≈ 0; half the days are positive. Median trade +2.6%, win rate 58%.
- So the edge, if real, is "**buy the bounce after a market-wide crash day**": a rare event (~1 per year in this
  sample), many coins at once. Three events cannot prove it. It beats random buying on the same days (p100), so the
  bounce after a crash is real in this sample, but the sample is 3 events.

## What this closes and what is left
- Closed: F2 (volume breakdown) and F3 (negative funding) as long signals in downtrends. Their 2021-23 mirror-image
  losses (shorts) did not turn into profit for longs after costs.
- Open, not tested: the crash-day bounce as an **event** (one market crash = one event, like the scanner's clustered
  alerts). Clean evidence can only come from new events. The way to collect it: log F1 forward in the hourly scanner,
  marked 🔴, and judge at a pre-set count of events.
