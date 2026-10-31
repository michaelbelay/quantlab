# Switcher - trade whichever book has been working, registered before the run (2026-10-24)

Michael 2026-10-24: "invent a strategy using strengths and weaknesses of the failed ones". The bear batch showed two
books that each earned for about a year and then flipped:
- Reversal book R (bear batch ideas 1 rally_short + 5 flush_long): earned 2024-04..2025-06, lost 2025-07..2026-09.
- Momentum book M (idea 10 weekly basket, long top 10 / short bottom 10 by 30-day change): lost or flat until 2025-06,
  earned 2025-07..2026-09.
Their weakness is the same: each works only in its own kind of market. Idea: hold the one that has been working lately.

## Rule (fixed now)
- Weekly, Monday 00:00 UTC. Weekly result of R = average net % of R trades opened that week (equal money per trade);
  of M = the basket's weekly net %. Costs as in the bear batch (0.20% per round trip).
- Next week: trade the book with the higher average weekly result over the last 8 weeks, if that average is > 0;
  otherwise stay in cash.
- Period 2022-02 .. 2026-09 (all data; 2022-02..2024-03 only 99 coins), same 220-coin list, same code as bear_batch.py.

## Pass (fixed now)
- Average weekly result > 0 in at least 4 of the 5 years 2022, 2023, 2024, 2025, 2026 (2022 and 2026 partial),
- AND higher total than R alone and than M alone over the whole period.
- Otherwise 🔴. A pass is a 🟡 for a paper forward test, not a live strategy.

## Known limits
- R and M were picked after seeing 2024-04..2026-09; only 2022-02..2024-03 is fresh for them. The 8-week window is
  a single fixed choice, no grid.

## Result (automatic, rule unchanged)
per year, average weekly %: {2022: {'R': 0.43, 'M': -0.1, 'sw': 0.37}, 2023: {'R': -0.02, 'M': 0.25, 'sw': 0.33}, 2024: {'R': 0.23, 'M': 0.34, 'sw': 0.17}, 2025: {'R': 0.31, 'M': 1.31, 'sw': 1.82}, 2026: {'R': -0.37, 'M': 2.09, 'sw': 1.34}}
sum of weekly %: {'R': 31.7, 'M': 174.0, 'sw': 187.8} | picked {'M': 107, 'R': 87, 'cash': 44} | verdict 🟡 paper forward test


## Re-run without look-ahead (2026-10-24, rule unchanged; the first run let Monday's choice see reversal trades that closed later in the week; now the choice uses closed trades only, the week's profit uses trades opened that week)
per year, average weekly %: {2022: {'R': 0.43, 'M': -0.1, 'sw': 0.41}, 2023: {'R': -0.02, 'M': 0.25, 'sw': 0.47}, 2024: {'R': 0.23, 'M': 0.34, 'sw': 0.1}, 2025: {'R': 0.31, 'M': 1.31, 'sw': 1.9}, 2026: {'R': -0.37, 'M': 2.09, 'sw': 1.26}}
sum of weekly %: {'R': 31.7, 'M': 174.0, 'sw': 194.1} | picked {'R': 103, 'M': 94, 'cash': 41} | verdict 🟡 paper forward test
