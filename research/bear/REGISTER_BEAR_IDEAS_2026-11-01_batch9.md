# Bear ideas – batch 9, shallow-bear longs with a crash guard (registered 2026-11-01, before the run)

Rules: `RULES_BEAR.md` + A1 + A2 + A3. Same period, halves, costs, funding, stop-first, volume filter. Entries only on
bear days that are **not** deep bear (deep bear as in batch 6). Every trade also exits at the first daily close where
tomorrow is deep bear (crash guard). Nothing below changes after the run.

| # | name | entry (long, daily close, bear & not deep) | exit |
|---|---|---|---|
| L1 | uptrend_dip | coin close > its 50-day average (daily closes) and 7-day return <= 0 | 168h · stop 10% · crash guard |
| L2 | majors_dip | BTC and ETH, every such daily close | 168h · stop 8% · crash guard |
| L3 | leaders_hold | Sunday close: the 3 coins with the highest 30-day return | 168h · stop 12% · crash guard |

Expected trades (rough): L1 ~600 · L2 ~150 · L3 ~200. Seen beforehand: equal-weight drift +0.55% (A) / +1.73% (B) per
week after shallow-bear closes, so passing is more likely than for the shorts; that is not proof. Paper is the judge.
Worst case shown: worst trade, worst week, results inside 2022.

## Result
Run 2026-11-01, `bear_batch9.py`, rules unchanged. All three 🔴: the bounce exists on average, but rules catch it only
through a few huge trades.

| # | trades (A / B) | win | avg | half A | half B | 2x | months + | top-3-month share | w/o 10 best | worst week |
|---|---|---|---|---|---|---|---|---|---|---|
| L1 uptrend_dip | 282 (129/153) | 45.7% | +1.11% | -0.84% | +2.75% | +0.91% | 14/28 | 154% | -0.48% | 2023-12-25 week -75% (sum of trades) |
| L2 majors_dip | 196 (81/115) | 46.9% | -0.15% | +1.09% | -1.02% | -0.35% | 16/33 | – | -1.06% | 2025-02-24 week -38% |
| L3 leaders_hold | 157 (65/92) | 43.3% | +1.87% | -0.99% | +3.88% | +1.67% | 11/28 | 121% | -1.06% | 2024-01-08 week -37% |
