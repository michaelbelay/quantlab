# Batch P - range, breakout, attention, pullback, day-range families, registered 2026-10-13 before any result

Same frame as batch O (PIT top-10, fit 2022-24 chosen on the 6-slot account, test 2025-01..2026-09-21, 0.10%/side +
funding, 1x, stop k x daily move sigma, one trade per coin per side per 24h; overlap with FlowTrend reported).
(A new-listing short was considered and dropped before running: young coins are outside the coins this account trades.)

| id | family | long rule (short = mirror) | grid |
|---|---|---|---|
| P1 | spike fade in a flat market | |r10| <= 1.5 sigma (no 10d trend) and 24h return <= -k sigma -> long | k [2,2.5,3], hold [24,48]h, stop 3 |
| P2 | 20-day breakout with new money | close = highest close of 480h and zOI(24h) >= k -> long | k [1,1.5], hold [72,120]h, stop 3 |
| P3 | top-10 newcomer | 1st of month: coin in this month's top-10, not last month's, BTC 20d > 0 -> long; coin that left the top-10 while BTC 20d < 0 -> short (if it still has data) | hold [7,14]d, stop 3 |
| P4 | pullback to trend with buyers | 20d return > 0, close crosses below its 480h average (first in 72h), taker buy-share z(24h) >= k -> long | k [0.5,1], hold [72,120]h, stop 3 |
| P5 | day-range breakout with trend | 10d return > 0, first 4h (00-04 UTC) range broken upward later that day -> long at the next open, exit at 24:00 UTC | range >= [0, 0.5] sigma, stop at the other side of the range |

Pass bar as batch O. Running count before this batch: 42 families today.

## Results (batch_p.py -> batch_p_results.json), 2026-10-13: none pass
| family | chosen | fit | test | test account | grid+ |
|---|---|---|---|---|---|
| P1 spike fade flat | 2 sigma, 24h | +0.15% | +0.11% PF 1.06, 2026 -52 | 303 | 5/6 |
| P2 breakout + OI | k1, 72h | +0.39% acct 459 | +0.22% PF 1.07, 2025 -84 | 292 drop 42% | 4/4 |
| P3 top-10 newcomer | 14d | -0.12% (83) | -9.11% PF 0.24 (35) | 172 | 0/2 |
| P4 pullback + buyers | k1, 72h | +0.02% (63) | -1.87% (32) | 271 | 0/4 |
| P5 day-range breakout | 0.5 sigma | -0.27% | -0.09% PF 0.93 | 231 | 0/2 |
Observation only (post-hoc, not a result): coins that newly enter the top-10 lost ~9% in their next 14 days in
2025-26 (but ~0 in 2022-24) - "short the newcomer" would need its own registration and fit support, which it lacks.
