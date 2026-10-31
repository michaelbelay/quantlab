# Protocol C — continuous intraday futures research (fixed 2026-10-05, before any run)

Goal: crypto perpetual-futures strategies on **15m / 30m / 1h**, long AND short, for a **300 USDT** account.
Failures are research input: each failed family gets a written diagnosis and a mutation (V2, V3 …) that
targets the diagnosed cause. No family is tuned over large grids; mutation > optimisation.

## Data
| Timeframe | Coins | Period | Source |
|---|---|---|---|
| 1h | ALL 413 (point in time, incl. dead coins) | 2021-01 → 2026-09 | old-bot 1h futures + funding (read-only) |
| 15m, 30m | 30 desk coins (taker-buy volume = volume delta) | 2024-09 → 2026-09 | desk 15m klines + funding; 30m resampled |

## Splits (time-based; nothing tuned on VALID)
- 1h: DEV 2021-01-01 → 2024-06-30 · VALID 2024-07-01 → 2026-03-25 · walk-forward 8 half-years 2022H2 → 2026H1
- 15m/30m: DEV 2024-09-01 → 2025-08-31 · VALID 2025-09-01 → 2026-03-25 · walk-forward 4 quarters
- 2026-03-26 → 09-25 is not used for selection (it was scored in F18's FINAL). The final judge is a **forward
  paper test on live public data** from the day a candidate passes.

## Execution model
- Signal on bar close → entry at the NEXT bar's open. No intrabar information before the signal bar closes.
- Costs per side: fee 0.05% + slippage 0.05%; stops add 0.05% extra slippage; a bar opening beyond the stop
  fills at the open. "2x costs" doubles fee and slippage.
- Exit: stop (ATR multiple), take-profit (ATR multiple), max holding time, optional opposite signal.
  If stop and take-profit are both inside one bar, the STOP is assumed first (pessimistic).
- Funding charged for every funding event a position is open through.
- Coin eligible at entry: ≥ 30 days listed, ≥ 10M USDT traded in the previous 24h.

## Portfolio (300 USDT, compounding)
Default book: 20 slots, stake = equity / 20 per position (15 USDT at start), ≤ 10 positions in one
direction, leverage 1x (2x and 3x reported, never chosen if liquidations appear). Per-coin minimum
order respected (BTC 50, ETH/LINK/BCH/LTC/ETC 20, others 5 USDT): an order below it is skipped.
"Balanced" variant: longs and shorts may differ by at most 2 open positions — reported for every family.

## Gates
DEV: ≥ 200 trades · PF ≥ 1.15 after costs · PF ≥ 1.00 at 2x costs · portfolio max DD ≤ 35% ·
≥ 3 of 4 periods positive (1h: 2021, 2022, 2023, 2024H1; 15m/30m: 4 quarters) · total above the 95th
percentile of 100 random-entry twins (same coins, sides, exits, holding) · top coin ≤ 20% of profit.
VALID (same rules, no change): PF ≥ 1.10 · profit at base and 2x costs · DD ≤ 40%.
WALK-FORWARD: ≥ 5 of 8 half-years (1h) / 3 of 4 quarters (15m/30m) positive.
Pass all three → forward paper test (minimum 60 days or 100 trades before any live discussion).

Every run is appended to `runs/ledger_c.jsonl` with family, version, timeframe, universe group, metrics,
gate results and the diagnosis. Metrics tracked per spec: net, CAGR, max DD, PF, Sharpe, Sortino, win rate,
average/median trade, trades and trades/year, long vs short, worst month/year, max consecutive losses,
exposure, return/DD.

## Implementation note (2026-10-09)
The WALK-FORWARD gate above was documented but not enforced by `quant/eval_c.py` until 2026-10-09 (only
`run_c40.py` reported it). It is now stage `wf` (refused without a recorded VALID pass). The last 1h half-year
(2026H1) is cut at 2026-03-26 because data from then on is not used for selection; 15m/30m use the last 4 quarters
before that date (Q3–Q6). No recorded verdict changes: no family has passed VALID.
Also 2026-10-09: the "2x and 3x reported" promise above had no code path (every `replay` call ran 1x). `eval_c.evaluate`
now writes `book_lev2` / `book_lev3` (final, PF, DD, Sharpe, liquidations) — reported, never gated. Ledger rows before
2026-10-09 are 1x only. Random twins raised from 100 to 2,000 (`gen_c.REPS`).
