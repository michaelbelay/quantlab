# Fresh search, batch B - registered 2026-10-13, before any result

Michael: "no keep search broaden more". Universe for every family: point-in-time top-10 Binance futures coins by
last month's traded value (stablecoins/indices excluded), re-ranked monthly (the coins a 300 USDT bot would trade).
1h data 2021-01 -> 2026-09-21, 0.10% per side, funding paid. Each family has a small fixed grid; the setting is
chosen ONLY on FIT 2022-01 -> 2024-12 by the 300 account result (3 slots, equity/3, 1x), then TEST 2025-01 -> 2026-09-21.
(Michael 2026-10-13, before any result: fit on 2022-2024 instead - one bear year and one bull year. 2021 is warm-up only, no trades.)

| id | family | rule (grid in brackets) |
|---|---|---|
| B1 | strength rotation | each Monday 00:00 UTC, if BTC 20d return > 0: long the 3 top-10 coins with the best [14,30,60]d return, hold 7d |
| B2 | weekly losers bounce | each Monday, if BTC 20d > 0: long the 3 top-10 coins with the worst [7,14]d return, hold [3,7]d |
| B3 | rip in downtrend (short) | [10,20]d return < 0 and 24h rise >= [1.5,2,2.5] x normal daily move -> short next open, stop 3x, exit [48,72]h |
| B4 | flash dip | 1h drop >= [3,4] x normal hourly move and volume >= [3,5]x its 30d hourly average -> long, exit [12,24]h, stop 2x daily move |
| B5 | quiet pullback | [10,20]d return > 0, 3 down days in a row, each day's volume below its 30d average -> long [72,120]h, stop [2,3]x daily move |
| B6 | NR7 breakout | daily range smallest of 7 days, next day breaks that day's high (long) / low (short) -> hold [2,4] days, stop at the other side of the NR7 day |
| B7 | 55-day breakout (turtle) | daily close above the 55d high -> long / below 55d low -> short, exit at the [10,20]d opposite extreme or [20,40] days |
| B8 | BTC trend + alt beta | when BTC 20d > 0 and BTC crosses above its [50,100]d average, long the 3 top-10 coins with highest 30d beta to BTC, hold [7,14]d |
| B0 | dip in uptrend (S7) again | S7's 81-setting grid, re-chosen on the new FIT window |
| B9 | dip in uptrend x rip in downtrend | S7-PIT longs + B3 shorts in one 3-slot account (the two chosen settings, no new choice) |

Pass bar: TEST trades >= 30, TEST avg > 0, TEST PF >= 1.2, BOTH test years (2025, 2026) positive, FIT avg > 0;
plus the 300 account on TEST ends above 300. Every result is reported. No unseen/held-out coin sets.

## Results batch B (batch_b.py -> batch_b_results.json; grids b_grid.py)
No family passes. B0 (S7 re-chosen on 2022-24) test +0.21%/trade, 2026 -47. B1 rotation, B4 flash dip, B5 quiet
pullback, B6 NR7, B7 turtle: fail. B2 losers +0.33% but 2025 negative. B8 alt beta: only 1 of 4 settings works (luck).
B3 rip in downtrend (short): test positive in 11/12 settings (+0.6..+2.2%/trade); history: 2022 (bear) positive,
2023/2024 (bull) negative -> a bear-market strategy.

## Follow-up C1, registered before running (2026-10-13)
C1 = B3 only while BTC's 20d return < 0 (bear), plus B0 only while BTC's 20d return > 0 (bull), one 3-slot account.
Same grids; each part's setting chosen on FIT 2022-2024 only; then TEST 2025-01..2026-09. Same pass bar.

## Result C1 (c1_switch.py): FAIL
Chosen on 2022-24: rip-short (2.5 sigma, 10d, 48h), dip-long (1.5 sigma, 72h, stop 3, 10d). Bear-only rip-short test 34
trades +1.29% PF 1.54 but account 284; bull-only dip-long test +0.36% PF 1.17; together test 191 trades +0.53% PF 1.24,
account 300 -> 326, drop 37%, 2025 +174, 2026 -74 (sum of %). 2026 is negative for every long family so far.
