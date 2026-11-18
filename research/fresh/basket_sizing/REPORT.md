# Basket sizing result (automatic, rule unchanged)

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
