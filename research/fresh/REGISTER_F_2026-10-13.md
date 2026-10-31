# Order-flow families - registered 2026-10-13, before any flow data was looked at

New data never used in this project: Binance USD-M 1h taker-buy volume (data.binance.vision public archives),
user_data/flow_data/. Idea source: Kim & Hansen 2026 (arXiv 2607.09426) report order imbalance forecasting 4-12h
returns on Binance perpetuals. Same frame as batch B: point-in-time top-10 coins, fit 2022-2024 (setting chosen on
the 300 account, 3 slots, equity/3, 1x), test 2025-01 -> 2026-09-21, 0.10%/side + funding.

buy share = taker-buy quote / quote volume over a window; z = (share - its 30d mean) / its 30d sd.

| id | family | rule (grid) |
|---|---|---|
| F1 | flow continuation | buy-share z over the last [4,12]h >= [2,3] -> long; <= -[2,3] -> short; hold [8,24]h, stop 2x daily move |
| F2 | absorption | 24h return <= -1x daily move but 24h buy-share z >= [1.5,2] -> long (mirror: up + selling -> short); hold [24,48]h, stop 2x |
| F3 | flow in trend | 10d return > 0 and 24h buy-share z >= [1,1.5,2] -> long [24,48]h, stop 2x (mirror short in downtrend) |
| F4 | flow rank, neutral | daily 00:00: long the 2 top-10 coins with the highest 24h net flow ((buy - sell)/total), short the 2 lowest, hold [24,72]h |
| F5 | exhaustion | buy-share z <= -[3,4] over 4h with 4h return <= -2x hourly-scaled move -> long [12,24]h (sellers exhausted); mirror short |

Pass bar: TEST >= 30 trades, avg > 0, PF >= 1.2, 2025 and 2026 both positive, FIT avg > 0, test account > 300.
Also reported: how many grid settings are positive on test (one lucky setting is not a result).

## Results (flow_test.py -> flow_results.json; checks f3_check.py), 2026-10-13
F1 continuation, F2 absorption, F4 flow rank (neutral), F5 exhaustion: fail.
**F3 flow in trend: PASS.** Chosen on 2022-24: buy-share z(24h) >= 2, hold 48h, stop 2x daily move; long in 10d uptrend,
short in 10d downtrend. Fit 1,163 trades +0.60%; TEST 778 trades +0.60%/trade, PF 1.29, 2025 +440 / 2026 +25 (sum %).
Account 3 slots 1x: test 300 -> 490 (drop 32%); 2022-2026 300 -> 1,917 (drop 35%). 2x: drop 56-65%, too deep.
Checks: double cost still +0.40%/trade; stronger flow = better (z 1: ~0, 1.5: ~0, 2: +0.4/+0.6) - only the z 2 extreme
carries the edge; shorts better than longs (test +0.75 vs +0.40); years 2022 +506, 2023 -15, 2024 +201, 2025 +440,
2026 +25; 20/30 coins positive, without top 3 coins +225; WEAK: without the best 10 test days the sum falls 465 -> 22.
Status 🟡 lead "F3 flow-in-trend" - best result of 2026-10-13. Live needs taker-buy volume per hour (Binance klines
field 9/10; the old bot's stored candles drop it) -> needs a small data add-on before any bot.
