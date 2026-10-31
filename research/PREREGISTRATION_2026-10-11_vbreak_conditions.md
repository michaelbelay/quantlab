# VBreak4 by market condition — pre-registered 2026-10-11, before this split was computed

## Why
Michael (2026-10-11): VBreak4Live is suitable in certain market conditions; judging it by its all-condition average
on the 280 unseen coins alone is unfair (those coins lean towards small and dead coins it never traded live, while the
133-coin list it traded is chosen with hindsight). This test asks: on the coins it would really have traded at the time,
in which market condition does it earn?

## Strategy and trades (frozen, nothing re-run or re-tuned)
VBreak4Both rules = pipeline candidate `focus-val1-vbreak4both` (volatility_breakout bars=4 atr_mult=2.0, btc_regime +
volume filters, both directions, ATR 2.0 stop, no TP, opposite-signal exit, 400-bar time exit, 1x). Trades as recorded on
2026-10-04: `research/pipeline/trades/focus-val1-vbreak4both__dev.parquet` (133 coins) + `__oos.parquet` (280 coins).
`pnl` is per 100 USDT notional, net of fee 0.05% + slippage 0.05% per side and funding. 2x costs = pnl − 0.20.
VBreak4Live = VBreak4Both + refuse-only risk gates (it can only take fewer trades); the gates are not modelled.

## Universe: point in time, no hindsight
All 413 coins. A trade counts only if, on its entry date, the coin ranks <= 133 by average daily traded volume over the
previous 30 days (`C:\quantlab\data\liq_rank.parquet`, known at the start of the day). 133 = the size of the live list.

## Market conditions (fixed definitions from earlier work, BTC daily, last completed close before entry)
- Bull / Bear: BTC 20-day return > 0 / <= 0 (the live MajorsTrend rule; the UI market badge).
- Wild / Calm: BTC 20-day realised volatility (std of daily returns) > / <= its median over the previous 365 days
  (the 2026-10-07 regime-switch definition). BTC daily history: spot 2017-08 → 2020-12 (`user_data/oot_data`) +
  futures 1d from 2021-01.
Four cells: Bull-Calm, Bull-Wild, Bear-Calm, Bear-Wild. Also reported: Bull, Bear, and all conditions together.

## Period
Every recorded trade, entry 2021-01-01 → 2026-09 (the full recorded span; the whole span was already seen in aggregate
on 2026-10-04, so the per-year table is reported to show consistency, not as a hold-out).

## Pass rule per cell (all required)
- >= 200 trades
- PF >= 1.15 at base costs and PF >= 1.05 at 2x costs (trade level)
- positive in >= 2/3 of the calendar years in which the cell has >= 20 trades
- 300 USDT portfolio trading ONLY in that cell (20 slots, <= 10 same direction, stake = equity/20, 1x, real minimum
  orders; `C:\quantlab\quant\book.py` replay): ends above 300 and max drawdown <= 40%
Known in advance: 2022 (bear) was positive on the unseen coins. Four cells are tested (+4 trials).

## Decision
A passing cell: reported to Michael with its numbers; he decides how to use VBreak4Live in that condition.
No cell passes: reported plainly, with the per-cell numbers.
Runner: `research/vbreak_conditions.py` → `research/VBREAK_CONDITIONS_RESULT_2026-10-11.md` + `.json`.
