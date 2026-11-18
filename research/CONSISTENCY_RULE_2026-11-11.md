# Consistency rule (Michael, 2026-11-11)

Michael 2026-11-11: "I need a consistent strategy and not a strategy that just enters once or twice in a year."

From now on every new idea, in every lab, is judged on frequency and regularity BEFORE anything else. A strategy that
earns its history on a handful of days is not a candidate, however good its total looks.

## The rule (fixed now)

Frequency, on the full history window of the test:
- all-market strategies: at least 3 trades per week on average AND at least one trade in 80% of all weeks;
- bear-only ideas (bear lab): entries on at least 25% of bear days AND at least 40 trades per year of history.

Regularity, same window:
- at least 60% of calendar months positive;
- every full calendar year positive;
- the best 3 entry days together make at most 25% of the total profit;
- longest stretch of the account under its last equity high: at most 16 weeks.

An idea that fails frequency is not entered into any paper test. An idea that passes frequency but fails regularity
is reported with the failing numbers and parked. Nothing is tuned afterwards to pass; a changed idea is a new idea.

## Where the lab stands against the rule (2026-11-11, from the records already on disk)

| strategy | trades / week | weeks active | months positive | years positive | longest under high | verdict |
|---|---|---|---|---|---|---|
| bear lab carry family (cdeep_*) | ~14 entry DAYS per year | - | - | 2024 negative (cdeep_funding) | - | fails frequency |
| FlowTrend (paper trader, 20 coins) | 6.4 | 96% | 17 / 30 | 2024, 2025, 2026 all positive | 34 weeks (peak 2026-01) | frequency ok, regularity fails |
| FlowTrend on 220 coins, top 10 | 6.5 | 96% | 19 / 30 | 2026 negative | 34 weeks | regularity fails |
| Switcher (paper, weekly R / M / cash) | weekly basket, in market 78% of weeks | 100% decisions | quarters 15 / 19, weeks positive 46% | 2022-2026 all positive | 45 weeks | closest so far; R and M were chosen after seeing 2024-26 |
| scalp families (5 m) | hundreds | 100% | - | all negative after fees | - | fails regularity |

Sources: research/fresh/strat_bt/FlowTrendAll/result.json and its trade zips; research/fresh/bear_batch/switcher_weeks.csv;
research/fresh/scalp/result.json; the bear lab diagnostic of 2026-11-11 (scratch scripts, read-only).
