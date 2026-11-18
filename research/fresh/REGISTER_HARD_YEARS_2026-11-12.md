# Search from the hard years: weekly market-neutral baskets chosen on 2022-2023 only - registered before the run (2026-11-12)

Michael 2026-11-12: "ok start the search from 2022 2023 data". Reason: Switcher-3, the sized basket and FlowTrend all
earn from mid-2024 on and sit flat or lose in 2022-2023; whatever is chosen on 2025-26 inherits that hole. So this
search CHOOSES on 2022-02..2023-12 and only then looks at 2024-01..2026-09, unchanged. Rule: research/CONSISTENCY_RULE_2026-11-11.md.

## Common frame (fixed now)
- Every Monday 00:00 UTC, among the 220 Switcher coins with data (57 of them in early 2022, 66 in 2023, 220 today;
  coins join when their market starts, no dead coins - Michael's rule), rank by the family's signal, long the 10 best
  and short the 10 worst, equal weight, 50% of the account per side, hold 7 days to the next Monday, no stops.
  Fewer than 40 ranked coins -> the week is skipped (cash).
- Weekly result = (mean long return - mean short return) / 2 - 0.20% cost, PLUS the funding of the week: a long pays
  the coin's funding, a short receives it (8h settlements, actual rates). Price-only result is reported next to it.
- 1x, 100% of the account, 300 USDT book compounding. Period 2022-02-07 .. 2026-09-30, 1h futures candles and funding
  from data/market/main/binance/futures.

## Families and their fixed settings (nothing else)
- A reversal: k-day change, long the LOSERS / short the WINNERS; k in {3, 7, 14}.
- B momentum: k-day change, long the WINNERS / short the LOSERS; k in {30, 60, 90} (30 = the Switcher's M book).
- C volatility: k-day standard deviation of daily returns, long LOW vol / short HIGH vol; k in {14, 30, 60}.
- D funding: average funding over the last k days, long the most NEGATIVE / short the most POSITIVE; k in {3, 7, 14}.
- E attention: 7-day traded value / 90-day traded value (close x volume), long the QUIET / short the HOT; one setting.
- MIX: the average of the five chosen settings' weekly results (one fifth of the account each).

## Choice rule (fixed now)
Per family the setting with the most positive calendar months in 2022-02..2023-12 wins; tie -> higher sum of weekly %
in that window. 2024-01..2026-09 is not looked at before the choice (the script makes the choice itself).

## Pass (fixed now) -> 🟡 paper forward test, otherwise 🔴
A chosen setting (or MIX) passes if it meets the consistency rule on the FULL period 2022-02..2026-09
(>= 60% of months positive, every year 2022..2026 positive, best 3 weeks <= 25% of the total, longest stretch under
the equity high <= 16 weeks) AND its 2024-01..2026-09 sum of weekly % is > 0.

## Reported (no re-tuning after the run)
Every setting of every family: 2022-23 months positive and sum, 2024-26 months positive and sum. Each chosen setting
and MIX: the full consistency table (sum, avg/week, weeks +, months +, years +, best-3-weeks share, longest stretch
under the high with dates, 300 USDT book, worst drop), price-only vs with funding, average coins ranked per week.

## Known limits
Only 57-66 coins exist in the data in 2022-23, so the 10/10 baskets were a fifth of the market then and a twentieth
now. Weekly holds without stops. Spot/perp basis, slippage on thin coins and delistings mid-week are not modelled.
Nine settings per family is a small fixed menu, not a grid search; the choice is made on 2022-23 only.

## Result (automatic, rule unchanged)

## Menu (choice made on the 2022-23 columns only)

| family | k | 2022-23 months + | 2022-23 sum % | 2024-26 months + | 2024-26 sum % | coins ranked | chosen |
|---|---|---|---|---|---|---|---|
| A reversal | 3 | 9/23 | -49.1 | 10/33 | -158.0 | 118.2 |  |
| A reversal | 7 | 10/23 | -41.9 | 11/33 | -161.8 | 117.8 | yes |
| A reversal | 14 | 10/23 | -55.1 | 13/33 | -156.4 | 117.1 |  |
| B momentum | 30 | 13/23 | +23.6 | 20/33 | +231.2 | 115.6 | yes |
| B momentum | 60 | 12/22 | -18.3 | 20/33 | +200.9 | 113.9 |  |
| B momentum | 90 | 11/21 | -6.4 | 20/33 | +130.0 | 111.9 |  |
| C volatility | 14 | 11/23 | -68.2 | 15/33 | -183.1 | 117.4 |  |
| C volatility | 30 | 13/23 | -36.1 | 18/33 | -86.0 | 116.3 | yes |
| C volatility | 60 | 12/22 | -45.0 | 14/33 | -68.1 | 115.0 |  |
| D funding | 3 | 16/23 | +32.8 | 14/33 | -87.4 | 118.3 | yes |
| D funding | 7 | 15/23 | +27.2 | 18/33 | -67.4 | 118.1 |  |
| D funding | 14 | 15/23 | +8.4 | 16/33 | -130.5 | 117.7 |  |
| E attention | 7 | 9/23 | -41.5 | 18/33 | +21.2 | 111.7 | yes |

## Chosen settings on the full period 2022-02 .. 2026-09 (with funding)

| setting | sum weekly % | avg/week | weeks + | months + | years + | best 3 weeks | longest under high | 300 USDT book | worst drop | price-only sum | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A reversal k=7 | -203.7 | -0.842% | 42.6% | 21/56 | 1/5 | None% | 220 wk (2022-07-11 .. 2026-09-21) | 23.9 | -95.5% | -141.1 | 🔴 |
| B momentum k=30 | +254.7 | +1.053% | 53.7% | 33/56 | 4/5 | 33.1% | 83 wk (2022-03-14 .. 2023-10-09) | 2801.9 | -28.0% | 174.0 | 🔴 |
| C volatility k=30 | -122.1 | -0.505% | 47.9% | 31/56 | 2/5 | None% | 228 wk (2022-05-16 .. 2026-09-21) | 48.1 | -89.6% | -30.0 | 🔴 |
| D funding k=3 | -54.6 | -0.226% | 52.1% | 30/56 | 2/5 | None% | 79 wk (2025-03-24 .. 2026-09-21) | 126.8 | -78.9% | -246.7 | 🔴 |
| E attention k=7 | -20.3 | -0.084% | 52.5% | 27/56 | 2/5 | None% | 192 wk (2022-06-06 .. 2026-02-02) | 202.5 | -51.9% | 49.2 | 🔴 |
| MIX of the five | -29.2 | -0.121% | 49.2% | 28/56 | 2/5 | None% | 225 wk (2022-06-06 .. 2026-09-21) | 209.9 | -47.2% | - | 🔴 |

Per-year sum %: A reversal k=7: {2022: -4.2, 2023: -37.7, 2024: -21.2, 2025: -142.5, 2026: 1.9} | B momentum k=30: {2022: -2.5, 2023: 26.0, 2024: 18.1, 2025: 88.3, 2026: 124.8} | C volatility k=30: {2022: 14.1, 2023: -50.2, 2024: -27.1, 2025: 7.1, 2026: -66.0} | D funding k=3: {2022: 7.9, 2023: 24.9, 2024: -6.2, 2025: -36.9, 2026: -44.3} | E attention k=7: {2022: -6.7, 2023: -34.8, 2024: -11.7, 2025: 32.1, 2026: 0.8} | MIX of the five: {2022: 1.7, 2023: -14.4, 2024: -9.6, 2025: -10.4, 2026: 3.5}
Best 3 weeks: A reversal k=7: [('2026-07-13', 45.45), ('2026-09-21', 11.7), ('2026-06-29', 10.68)] | B momentum k=30: [('2025-08-04', 36.46), ('2026-03-16', 28.08), ('2026-02-16', 19.78)] | C volatility k=30: [('2025-12-22', 29.09), ('2026-09-21', 23.91), ('2025-03-03', 12.58)] | D funding k=3: [('2026-09-14', 18.67), ('2026-08-17', 12.67), ('2026-01-12', 10.22)] | E attention k=7: [('2024-02-12', 15.17), ('2026-01-19', 13.81), ('2025-07-07', 10.62)] | MIX of the five: [('2026-07-13', 7.48), ('2026-09-21', 7.27), ('2025-12-22', 6.08)]

