# Pre-registration: new strategy families (written before any result was seen)

Date: 2026-09-25. Author: Claude (cloud workspace, offline). The live bot was not touched.

## Data
- Binance USDT-M perpetuals, 1h OHLCV + actual funding events, 131 coins, 2021-01-01 to 2026-09-21.
- Coin split reused from the project: `split_140.json` (dev = even market-cap ranks, holdout = odd).
- **All selection happens on dev coins only.** Holdout coins are touched once per finalist.
- Known bias: the universe consists of coins listed today (survivorship). This favours long legs
  and penalises short legs. It applies equally to the live strategy's validation.

## Costs
- Base: 0.05% fee + 0.05% slippage per side (0.10% per side on traded notional), same as the project engine.
- Funding: actual historical funding events; longs pay positive funding, shorts receive it.
- Stress: 2x fee+slippage and 2x funding.

## Families (portfolio strategies, none tested in this project before)
1. **XS_MOM**: cross-sectional momentum. Rank coins by past return, long top N / short bottom N, periodic rebalance.
2. **CARRY**: funding carry. Short the coins with the highest trailing funding, long the lowest.
3. **TS_TREND**: daily time-series trend on each coin, volatility-scaled, equal risk across coins.
4. **XS_REV**: short-term cross-sectional reversal (expected to die on costs; included as a control).
5. **MOM+CARRY**: 50/50 blend of the best dev configs of 1 and 2 (only if both pass dev).

## Selection (dev coins)
- Small grids only (<= 48 configs per family). The config picked per family = best dev **Sharpe**
  among configs whose dev PF at 2x costs >= 1.05. Grid robustness: the median config of the
  family must have positive dev return, otherwise the family is rejected as a lucky pick.

## Gates for a PASS (holdout coins, picked config, no re-tuning)
1. Trade-level profit factor >= 1.15 at base costs.
2. Profit factor >= 1.10 at 2x costs AND >= 1.10 at 2x funding.
3. Max drawdown <= 25% (the live strategy's holdout drawdown was 34.9-37.4%).
4. Every regime >= 0 on holdout: 2021, 2022, 2023-24, 2025-26.
5. Walk-forward: parameters re-selected on dev coins in each training window (expanding, first
   test window starts 2022-07), applied to holdout coins in the next 6-month window.
   Sum of OOS returns > 0 and >= 5 of 8 folds positive.
6. Executable at the live account size: every position >= 5 USDT notional at 390 USDT equity.

A candidate that fails any gate is reported as FAIL with the gate named. No gate is relaxed after
results are seen.

## Amendment 1 (2026-09-25, after dev grid, BEFORE any holdout run)
Dev results showed single families with 40-70% drawdowns but near-zero correlation between
CARRY and the momentum/trend families (dev daily corr -0.02 to -0.09). Two additions, fixed now:
- **VT overlay**: portfolio volatility targeting. Exposure scale = min(20% / realised 30d vol of the
  unscaled strategy, gross cap 1.0). 20% is fixed, not tuned. Gross never exceeds 1.0 (live rule: 1x).
- **BLEND**: equal-risk blend of the dev-picked XS_MOM, CARRY and TS_TREND sleeves (each sleeve scaled
  to 20% vol, summed, then the VT overlay applied to the total).
Dev picks per the original rule (best dev Sharpe with dev PF@2x >= 1.05):
XS_MOM lb14 n5 every14 | XS_MOM_LONG lb14 n5 every14 btc_filter | CARRY lb7 n8 every7 ivol |
TS_TREND lb20 long-only ema every1. XS_REV rejected on dev (median config loses 94%).

## Round 1 holdout result (recorded as seen)
All round-1 candidates FAIL (see results.md). Best: TS_TREND long-only (PF 1.45, PF2x 1.39, DD 19.3%)
failed gate 4 (2022 -16.6%, 2025-26 -4.6%).

## Amendment 2 (round 2, written after round-1 holdout, BEFORE any round-2 run)
Round-1 losses concentrate in bear/chop regimes for long-biased sleeves. Round 2 tests two
regime-gated long families, selected on dev only with the same rule, same holdout gates:
- **TREND_GATED**: TS_TREND long-only, positions allowed only when BTC close > its N-day SMA (N in 50/100/200).
- **DUAL_MOM**: long top-n by past return, only coins whose own past return > 0, only when BTC > SMA(N);
  weekly/biweekly rebalance, equal weight, gross 1.0 when fully invested.
Round 2 is a second look at the same holdout coins, so a pass here carries more selection risk than a
round-1 pass; the report will say so.
