# Batch L - cross-asset lead-lag sniper (seconds), registered 2026-10-13 before any tick data was looked at

Outside review passed in by Michael: when BTC makes a sharp 30-60 s move, liquid alts that have not caught up yet
(relative to their usual BTC relationship) should follow; trade the lagging follower for 1-10 minutes.
(The 1h version, S8 "BTC leads", already failed in batch A - this is the seconds version.)

## Data (new, never used here)
Binance USD-M futures aggTrades, data.binance.vision daily files, 60 days 2026-07-23 .. 2026-09-20.
Built into 1-second last-trade prices (forward-filled). Leader BTC; followers ETH, SOL, XRP, DOGE, BNB.
FIT = first 30 days (07-23 .. 08-21), TEST = last 30 days (08-22 .. 09-20). No other coin sets.

## Rule
- beta of each follower = OLS slope of its 60 s returns on BTC 60 s returns over the PREVIOUS 24 h (no look-ahead).
- Event: BTC return over the last L s, |rB| >= q. Gap = beta x rB - rF (follower return over the same L s), signed in
  BTC's direction. If gap >= g: trade the follower in BTC's direction.
- Entry at the follower's price 1 s after the signal second (home-PC latency; a real order takes ~0.2-0.5 s plus queue).
- Exit after H s (time stop). One trade per follower per 60 s.
- Grid: L [30, 60] s, q [15, 25, 40] bps, g [10, 20] bps, H [60, 180, 600] s -> 36 settings; chosen on FIT net total.
- Markouts reported at 1, 5, 15, 60, 180 s after entry (gross, follower move in trade direction).

## Costs
0.10% per side (Michael's working assumption: taker fee + slippage) -> 0.20% round trip. Also reported at 0.05%/side
(taker fee alone with no slippage, the floor).

## Pass bar
TEST at 0.10%/side: >= 100 trades, avg net > 0, PF >= 1.2, at least half of the 36 settings net positive on test,
FIT net avg > 0. If the GROSS markout is below the round-trip cost, the idea is dead before order-book data or a
paper bot (no need to add book confirmation to a signal that cannot pay its costs).

## Results (get_ticks.py -> user_data/tick_data, leadlag.py -> leadlag_results.json), 2026-10-13: FAIL
60 days of 1 s futures prices, 6 coins (360 daily aggTrades files). Betas to BTC: ETH 1.14, SOL 1.24, XRP 1.14,
DOGE 1.20, BNB 0.68.
- **Gross move after entry is about zero**: across the 36 settings the test gross average is -0.39% .. +0.11% per trade,
  typically +0.01..+0.02% - against 0.20% round-trip cost. 0/36 settings net positive on test (or on fit).
- Chosen on fit (30 s, BTC >= 40 bps, gap >= 20 bps, hold 180 s): test 77 trades, net -0.26% (PF 0.40) at 0.10%/side,
  still -0.16% (PF 0.57) at the 0.05%/side floor. Markouts after entry: 1 s 0.00%, 5 s +0.04%, 15 s +0.08%, 60 s +0.11%,
  180 s -0.06% - even the best point (60 s, +0.11%) is about half of the cost.
- The followers catch up inside the first second: by the time a home PC could act, the gap is already closed. Dead
  before order-book data or a paper bot, as registered.
