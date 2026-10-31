# Batch V - options-market fear (Deribit DVOL) -> BTC/ETH perps, registered 2026-10-13 before any DVOL data was looked at

New data never used here: Deribit DVOL (30-day implied volatility index of BTC and ETH options), daily, public API
(get_volatility_index_data). Idea: option buyers' fear and its premium over realized volatility carry information
about the next days' returns (variance risk premium literature). Traded on Binance BTC and ETH perps, each with its
own DVOL.

Signals on the daily close (00:00 UTC), entry at the next 1h open, exit after H days, stop 3 x daily move.
z = (value - its 90-day mean) / its 90-day sd. RV30 = annualised sd of the last 30 daily returns, in vol points.
| id | family | rule | grid |
|---|---|---|---|
| V1 | panic buy | DVOL z >= k -> long | k [1.5,2], H [3,7] |
| V2 | variance premium | VRP = DVOL - RV30; VRP z >= k -> long; VRP z <= -k -> short | k [1,1.5], H [3,7] |
| V3 | fear fading | DVOL z was >= 1.5 in the last 5 days and DVOL fell over the last 3 days -> long | H [5,10] |
| V4 | complacency in a downtrend | DVOL z <= -k and 10d return < 0 -> short | k [1.5,2], H [3,7] |
One trade per coin per signal type until it closes. Account 300 USDT, 2 slots equity/2, 1x, 0.10%/side + funding.
FIT 2022-2024 (setting chosen on the fit account), TEST 2025-01..2026-09-21.
Pass bar: TEST >= 20 trades, avg > 0, PF >= 1.2, 2025 and 2026 both positive, FIT avg > 0, test account > 300,
at least half of the grid positive on test. Running count before this batch: 53 families today.

## Results (batch_v.py -> batch_v_results.json; checks v_check.py, v4_acct.py), 2026-10-13
| family | chosen | fit | test | test account (2 slots, 1x) | grid+ | verdict |
|---|---|---|---|---|---|---|
| V1 panic buy | 2, 7d | 36 trades +3.04% | 12 trades -0.42% | 290 | 1/4 | fail |
| V2 variance premium | 1.5, 7d | 111 +0.58% | 64 +1.05% PF 1.47, 2026 +1 | 400 drop 15% | 4/4 | pass by rule, WEAK |
| V3 fear fading | 5d | 62 -0.22% | 26 -1.16% | 256 | 0/2 | fail |
| **V4 complacency short** | 1.5, 7d | 53 +2.23% | 26 +2.19% PF 2.40 | 391 drop 7% | 4/4 | **PASS, robust** |

V4 checks: every year positive 2022 +74, 2023 +22, 2024 +22, 2025 +24, 2026 +33 (sum of %); both coins positive
(BTC +1.16%, ETH +3.11%/trade); all 24 neighbours (k 1.0-2.5 x H 3-10d) positive on test AND fit; double cost
+1.99%/trade; test without best 3 trades +0.94%; 75 distinct signal days of 79 trades. Weak point: few trades
(~16/year), half of the 2022-26 profit sits in the best 5 trades. Account 2022-26: 1x 300 -> 679 drop 14%;
2x 1,382 drop 27%; 3x 2,562 drop 37%. Test only (2025-26): 1x 391 drop 7%, 2x 491 drop 14%.
V2 is weaker: its fit is negative in 9 of 24 neighbours, its long and short sides each lose in some years, 2026 flat.
Status: V4 🟡 research lead ("DVOL complacency short"), the second real edge after FlowTrend, and a different one
(options data, BTC/ETH, short only, ~2 trades a month).
