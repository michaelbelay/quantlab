# Batch G - more order-flow families + spot flow, registered 2026-10-13 before any result

Michael: "keep searching for more strategies". Same frame as F: point-in-time top-10 coins, fit 2022-2024 (setting
chosen on the 300 account, 6 slots, equity/6, 1x - the size FlowTrend now runs), test 2025-01 -> 2026-09-21,
0.10%/side + funding. z = (buy share - its 720h mean) / its 720h sd; buy share = taker-buy quote / quote volume.
New data: SPOT 1h taker-buy volume (user_data/flow_spot, data.binance.vision spot archives).

| id | family | rule (grid) |
|---|---|---|
| G1 | slow flow in trend | as FlowTrend but the flow window is [72,168]h and the z bar [1.5,2]; hold [72,120]h, stop 2.5x |
| G2 | sustained flow | z(24h) >= 2 AND z(72h) >= [1,1.5] in the 10d trend direction (mirror short); hold 48h, stop 2x |
| G3 | market flow -> majors | mean z(24h) of the top-10 >= [1,1.5] -> long BTC+ETH; <= -[1,1.5] -> short; hold [24,48]h, stop 2x |
| G4 | own flow vs market | coin z(24h) minus the top-10 mean z >= [1.5,2] in the coin's 10d trend direction (mirror short); 48h, stop 2x |
| G5 | flow without crowding | FlowTrend signal but only if funding is not in the coin's top [10,20]% of the last 30 days (longs) / bottom (shorts) |
| G6 | spot-led buying | SPOT z(24h) >= [1.5,2] in a 10d uptrend while PERP z(24h) < spot z -> long (mirror short); 48h, stop 2x |
| G7 | spot vs perp divergence | spot z - perp z >= [2,2.5] -> long (spot buyers stronger than leveraged ones); <= -[2,2.5] -> short; 48h, stop 2x |

Pass bar: TEST >= 30 trades, avg > 0, PF >= 1.2, 2025 and 2026 both positive, FIT avg > 0, test account (6 slots)
> 300; reported with grid settings positive on test. Also reported for any pass: overlap with FlowTrend signals
(a copy of FlowTrend is not a new strategy). No unseen/held-out coin sets.

## Results (batch_g.py -> batch_g_results.json), 2026-10-13
- G2 sustained flow and G5 flow-without-crowding PASS the bar, but 100% of their signals are FlowTrend signals
  (filters of it): test 300 -> 422 (drop 21%) / 457 (drop 25%) vs FlowTrend itself ~445-490. Not new strategies, and
  not clearly better than FlowTrend -> FlowTrend stays as it is.
- G1 slow flow (72h window): fit strong (+1.44%/trade, account 1,303), 8/8 settings positive on test, but test only
  +0.29%/trade, PF 1.11 -> fail. 63% overlap with FlowTrend.
- G3 market flow -> BTC/ETH: +0.13%/trade, 2026 negative. G4 own flow vs market: test negative.
- Spot flow (new data, 55 coins): G6 spot-led buying ~0, G7 spot vs perp divergence negative. Spot taker flow adds
  nothing on top of futures flow here.
