# NFI at 2x instead of 3x - registered before the run (2026-10-22)

Michael 2026-10-22: "yes run the 2x backtest". Question: does 2x leverage remove NFI's rare big losses (liquidations,
-99% worst trade at 3x) while keeping most of the profit?

## Setup (identical to the 3x baseline research/fresh/nfi_bt_full223, one change)
- Same strategy file (research/fresh/nfi), same 219 coins (full223), same data (user_data/data_nfi), 5m, 6 slots,
  unlimited stake, isolated futures, 2024-04 .. 2026-09 in monthly chunks.
- ONLY change: futures_mode_leverage, futures_mode_leverage_rebuy_mode, futures_mode_leverage_grind_mode = 2.0
  (NFI's own config-safe parameters; the strategy file is not edited).
- Every month starts from 300 USDT (no compounding), so month returns compare directly with the 3x months
  (3x month return = end/start - 1 of its chain).

## Report (no re-tuning)
Per month return 2x vs 3x; months positive; total of monthly returns; worst trade; trades below -50% / liquidations;
deepest drop inside a month; trade count and win rate.
2x counts as better only if it has fewer trades below -50% AND keeps at least 70% of the 3x total monthly return.

## Result (automatic, rule unchanged)
3x +1844% vs 2x +1399% (76%); trades <= -50%: 3x 4, 2x 0; verdict: 2x better
