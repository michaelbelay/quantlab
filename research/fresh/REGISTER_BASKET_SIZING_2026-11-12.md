# Weekly basket, always in the market, regularity by sizing - registered before the run (2026-11-12)

Michael 2026-11-11: consistency rule (research/CONSISTENCY_RULE_2026-11-11.md). Switcher-3 (REGISTER_SWITCHER3_2026-11-12.md)
was 🔴: every book earns in bursts, so the switch inherits bursts. The most regular single book is the momentum
basket M (53% of weeks positive) but it spent 87 weeks under its high in 2022-23. This test keeps M's entries exactly
as they are and changes ONLY how much is put on. Michael 2026-11-12 00:40: "ok go".

## Entries (unchanged from switcher.py)
Every Monday 00:00 UTC, among the 220 coins with data: long the 10 strongest and short the 10 weakest by 30-day
change, held 7 days to the next Monday, no stops. Costs 0.20% per round trip per unit of exposure. 1x, never above
100% of the account (no leverage). Period 2022-02-07 .. 2026-09-30.

## Sizing variants (fixed now, nothing else)
- B0 baseline = M as it is: equal weight, 100% of the account every week (50% long, 50% short).
- B1 book vol target: exposure e = min(1, 3% / sd), sd = standard deviation of the last 13 finished B0 weekly
  results (at least 8 weeks; before that e = 0.5). Equal weights inside the legs.
- B2 inverse-vol legs: inside each leg a coin's weight is proportional to 1 / its 30-day daily-return standard
  deviation (daily closes at 00:00 UTC), weights sum to 50% per leg. Missing sd = the leg's median sd. Full exposure.
- B3 = B2 weights with B1's exposure rule (sd taken from B2's own weekly results).

## Reported (no re-tuning after the run)
For B0..B3: per-year average weekly %, sum of weekly %, weeks positive, months positive, years positive, share of
the total made by the best 3 weeks, longest stretch under the equity high (weeks, with dates), 300 USDT book
(compounding) final and worst drop, average exposure, and for B2/B3 the smallest and median leg at 300 USDT
(Binance futures minimum is about 5 USDT per order - legs below it could not be placed as they are).

## Pass (fixed now) -> 🟡 paper forward test, otherwise 🔴
A variant passes if it meets the consistency rule: >= 60% of months positive, every year 2022..2026 positive,
best 3 weeks <= 25% of the total, longest stretch under the equity high <= 16 weeks.

## Known limits
M's entry rule was chosen after seeing 2024-04..2026-09 (bear batch idea 10); 2022-02..2024-03 is the fresh part.
Weekly holds without stops; a coin delisted mid-week is not modelled (today's 220 list, Michael's rule).
Vol target 3% and 13 weeks are single fixed choices, no grid.

## Result (automatic, rule unchanged)

| variant | sum weekly % | avg/week | weekly sd | weeks + | months + | years + | best 3 weeks | longest under high | 300 USDT book | worst drop | avg exposure | rule |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 equal weight, full | +174.0 | +0.731% | 5.05% | 52.9% | 32/56 | 4/5 | 45.2% | 87 wk (2022-03-14 .. 2023-11-20) | 1281.2 | -29.3% | 100.0% | fail |
| B1 vol target 3% | +91.2 | +0.383% | 3.3% | 52.9% | 32/56 | 4/5 | 47.4% | 84 wk (2022-03-14 .. 2023-10-30) | 657.7 | -21.8% | 75.1% | fail |
| B2 inverse-vol legs | +144.1 | +0.606% | 4.79% | 52.5% | 33/56 | 4/5 | 35.5% | 100 wk (2022-03-14 .. 2024-02-19) | 969.2 | -33.9% | 100.0% | fail |
| B3 inverse-vol + vol target | +104.5 | +0.439% | 3.22% | 52.5% | 33/56 | 4/5 | 34.8% | 85 wk (2022-03-14 .. 2023-11-06) | 754.5 | -20.5% | 71.4% | fail |

Per-year sum %: B0 equal weight, full: {2022: -4.2, 2023: 12.8, 2024: 17.8, 2025: 68.1, 2026: 79.4} | B1 vol target 3%: {2022: -2.7, 2023: 13.2, 2024: 15.5, 2025: 30.9, 2026: 34.4} | B2 inverse-vol legs: {2022: -5.6, 2023: 11.2, 2024: 8.0, 2025: 74.1, 2026: 56.5} | B3 inverse-vol + vol target: {2022: -3.2, 2023: 11.7, 2024: 19.6, 2025: 45.7, 2026: 30.6}
Best 3 weeks: B0 equal weight, full: [('2025-08-04', 32.01), ('2026-03-16', 27.41), ('2026-02-16', 19.28)] | B1 vol target 3%: [('2025-08-04', 22.5), ('2026-02-16', 10.38), ('2026-03-16', 10.31)] | B2 inverse-vol legs: [('2026-03-16', 20.97), ('2025-03-03', 15.81), ('2024-11-25', 14.35)] | B3 inverse-vol + vol target: [('2024-11-25', 14.35), ('2026-03-16', 11.31), ('2024-07-01', 10.72)]
Leg sizes at 300 USDT (inverse-vol): B2 inverse-vol legs: min 0.0, median 14.4 | B3 inverse-vol + vol target: min 0.0, median 9.19

**Verdict: {'B0 equal weight, full': '🔴', 'B1 vol target 3%': '🔴', 'B2 inverse-vol legs': '🔴', 'B3 inverse-vol + vol target': '🔴'}**
