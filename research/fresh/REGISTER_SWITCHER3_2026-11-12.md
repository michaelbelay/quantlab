# Switcher-3 - the Switcher with FlowTrend as a third book, registered before the run (2026-11-12)

Michael 2026-11-11: "I need a consistent strategy and not a strategy that just enters once or twice in a year" -> rule
research/CONSISTENCY_RULE_2026-11-11.md. The Switcher (REGISTER_SWITCHER_2026-10-24.md) is the only engine in the lab
that decides every week and was positive in every year of history; its weak spot is 45 weeks under its equity high.
Question: does a third book that trades 6 times a week (FlowTrend) make the weekly result more regular?
Michael 2026-11-11 23:50: "ok go".

## Books (fixed now)
- R reversal book: rally_short + flush_long, exactly as bear_batch.py / switcher.py (unchanged).
- M momentum basket: Monday long top 10 / short bottom 10 by 30-day change, 7 days, exactly as switcher.py (unchanged).
- F flow book = FlowTrend's rule on the same 220 coins, as in the 10-28 FT-10 run:
  buy share = taker-buy quote / quote volume over 24h; z = (share - 720h mean) / 720h sd (min 500h);
  LONG if 240h log return > 0 and z >= 2, SHORT if 240h return < 0 and z <= -2; only coins in the month's top 10 by
  LAST calendar month's traded value (close x volume, among the 220, coins with >= 480 hours that month);
  one signal per coin and side per 24h; one open trade per coin; entry at the signal candle's close;
  stop = 2 x daily move (sd of 1h log returns over 720h x sqrt 24) from entry, checked on the next candles' high/low;
  exit 48h after entry. 1x. Costs 0.20% per round trip like R and M (FlowTrend's own backtests used 0.10%; the
  stricter figure is used here so the books are comparable). Funding not counted (as before).
- Weekly result of F = average net % of F trades opened that week (equal money per trade), like R.
  Known by Monday = trades closed by then, like R.

## Switch rule (fixed now, same as the 10-24 re-run)
Monday 00:00 UTC: for each book the average of the last 8 finished weeks of what was KNOWN (R, F: closed trades;
M: finished weeks). Trade the book with the highest average if it is > 0, otherwise cash. Ties: R before F before M.
Period 2022-02-07 .. 2026-09-30, the 220-coin list of the Switcher, 1h futures candles data/market/main/binance/futures,
taker flow data/market/flow (data.binance.vision, fetched 2026-10-13..28).

## Reported (no re-tuning after the run)
For R, M, F alone, the current Switcher (R/M) and Switcher-3 (R/F/M): per-year average weekly %, sum of weekly %,
weeks positive, months positive, years positive, share of the total made by the best 3 weeks, longest stretch under
the equity high in weeks, weeks in cash, and a 300 USDT book (weekly % applied to the whole account, compounding, as
the 10-24 register's "sum of weekly %" but compounded) with final equity and worst drop. For F alone also trades per
week and share of weeks with a trade (the consistency rule's frequency test).

## Pass (fixed now) -> 🟡 paper forward test, otherwise 🔴
Switcher-3 must meet the consistency rule: >= 60% of months positive, every year 2022..2026 positive, best 3 weeks
<= 25% of the total, longest stretch under the equity high <= 16 weeks; AND it must beat the current Switcher on both
the sum of weekly % and the longest stretch under the high (otherwise the third book adds nothing).

## Known limits
R and M were chosen after seeing 2024-04..2026-09; FlowTrend's settings were chosen on 2022-2024 and the 220-coin F-10
variant was seen on 2024-04..2026-10 (10-28 run). Only 2022-02..2024-03 is fresh for all three books together.
The 220 list is today's list (no dead coins, Michael's rule); coins join when their market starts.

## Result (automatic, rule unchanged)

| book | sum weekly % | avg/week | weeks + | months + | years + | best 3 weeks share | longest under high | 300 USDT book | worst drop | rule |
|---|---|---|---|---|---|---|---|---|---|---|
| R | +31.7 | +0.133% | 46.6% | 31/56 | 3/5 | 0.7% | 48 wk | 379.6 | -24.4% | fail |
| F | +88.6 | +0.372% | 47.9% | 28/56 | 4/5 | 0.6% | 70 wk | 593.3 | -34.7% | fail |
| M | +174.0 | +0.731% | 52.9% | 32/56 | 4/5 | 0.5% | 87 wk | 1281.2 | -29.3% | fail |
| switcher_RM | +194.1 | +0.815% | 45.8% | 34/56 | 5/5 | 0.4% | 45 wk | 1673.2 | -23.6% | fail |
| switcher_RFM | +222.8 | +0.936% | 51.7% | 35/56 | 5/5 | 0.3% | 41 wk | 2145.1 | -18.5% | fail |

F alone: 1628 trades = 6.74/week, a trade in 97.5% of weeks, avg +0.443%/trade, win 48.2%, {'short': 962, 'long': 666}.
Per-year sum % - R {2022: 18.4, 2023: -1.1, 2024: 12.4, 2025: 16.2, 2026: -14.1} | F {2022: 22.7, 2023: 4.5, 2024: -3.9, 2025: 52.7, 2026: 12.6} | M {2022: -4.2, 2023: 12.8, 2024: 17.8, 2025: 68.1, 2026: 79.4} | Switcher R/M {2022: 17.6, 2023: 24.3, 2024: 5.1, 2025: 99.0, 2026: 48.0} | Switcher R/F/M {2022: 18.7, 2023: 18.7, 2024: 10.0, 2025: 114.9, 2026: 60.4}
Picked: R/M {'R': 103, 'M': 94, 'cash': 41} | R/F/M {'R': 78, 'M': 74, 'F': 62, 'cash': 24}
Check: Switcher R/M sum here 194.1 vs 194.1 in the 10-24 re-run.

**Verdict: 🔴**

## Result (automatic, rule unchanged; re-run 2026-11-12 00:30 after fixing the 'best 3 weeks share' column, which printed a ratio instead of a percent - numbers otherwise identical)

| book | sum weekly % | avg/week | weeks + | months + | years + | best 3 weeks share | longest under high | 300 USDT book | worst drop | rule |
|---|---|---|---|---|---|---|---|---|---|---|
| R | +31.7 | +0.133% | 46.6% | 31/56 | 3/5 | 69.0% | 48 wk (2025-10-27 .. 2026-09-21) | 379.6 | -24.4% | fail |
| F | +88.6 | +0.372% | 47.9% | 28/56 | 4/5 | 63.5% | 70 wk (2023-10-30 .. 2025-02-24) | 593.3 | -34.7% | fail |
| M | +174.0 | +0.731% | 52.9% | 32/56 | 4/5 | 45.2% | 87 wk (2022-03-14 .. 2023-11-20) | 1281.2 | -29.3% | fail |
| switcher_RM | +194.1 | +0.815% | 45.8% | 34/56 | 5/5 | 38.2% | 45 wk (2024-01-08 .. 2024-11-11) | 1673.2 | -23.6% | fail |
| switcher_RFM | +222.8 | +0.936% | 51.7% | 35/56 | 5/5 | 33.3% | 41 wk (2024-03-18 .. 2024-12-23) | 2145.1 | -18.5% | fail |

F alone: 1628 trades = 6.74/week, a trade in 97.5% of weeks, avg +0.443%/trade, win 48.2%, {'short': 962, 'long': 666}.
Per-year sum % - R {2022: 18.4, 2023: -1.1, 2024: 12.4, 2025: 16.2, 2026: -14.1} | F {2022: 22.7, 2023: 4.5, 2024: -3.9, 2025: 52.7, 2026: 12.6} | M {2022: -4.2, 2023: 12.8, 2024: 17.8, 2025: 68.1, 2026: 79.4} | Switcher R/M {2022: 17.6, 2023: 24.3, 2024: 5.1, 2025: 99.0, 2026: 48.0} | Switcher R/F/M {2022: 18.7, 2023: 18.7, 2024: 10.0, 2025: 114.9, 2026: 60.4}
Picked: R/M {'R': 103, 'M': 94, 'cash': 41} | R/F/M {'R': 78, 'M': 74, 'F': 62, 'cash': 24}
Check: Switcher R/M sum here 194.1 vs 194.1 in the 10-24 re-run.
Best 3 weeks: R/M [('2025-08-04', 32.01), ('2026-03-16', 27.41), ('2025-09-01', 14.81)] | R/F/M [('2025-08-04', 32.01), ('2026-03-16', 27.41), ('2025-09-01', 14.81)]

**Verdict: 🔴**
