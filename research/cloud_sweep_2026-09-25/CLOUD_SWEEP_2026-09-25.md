# New strategy families: verdict (2026-09-25)

Run offline in Claude's cloud workspace on a copy of the Binance futures data (131 coins,
2021-01 to 2026-09, 1h OHLCV + real funding). The live bot and this folder were not touched,
except for adding this report.

## Verdict
**0 of 12 candidates pass. Keep VBreak4Live unchanged.**
Rules were fixed before any holdout result was seen (see PREREGISTRATION section below).

## Holdout coins (62 coins never used for selection)

| Candidate | PF | PF 2x costs | Max DD | CAGR | 2022 | 2025-26 | Failed gates |
|---|---|---|---|---|---|---|---|
| TREND_GATED (long trend, BTC>SMA50 gate) | **1.53** | **1.45** | **19.4%** | 10.2% | -14.1% | +6.2% | regime (2022) |
| TS_TREND long-only | 1.45 | 1.39 | 19.3% | 9.1% | -16.6% | -4.6% | regime |
| XS_MOM long-only + BTC filter | 1.59 | 1.53 | 71.9% | 41.1% | -34.3% | +35.2% | DD, regime |
| XS_MOM long-only + vol target | 1.39 | 1.33 | 34.3% | 12.6% | -23.7% | +15.6% | DD, regime |
| DUAL_MOM | 1.49 | 1.44 | 81.3% | 36.0% | -47.1% | -4.8% | DD, regime |
| TS_TREND + vol target | 1.35 | 1.29 | 33.9% | 16.3% | -26.9% | -7.1% | DD, regime |
| XS_MOM long/short | 1.12 | 1.09 | 60.6% | 15.6% | -0.9% | -17.2% | PF, costs, DD, regime |
| XS_MOM long/short + vol target | 1.08 | 1.04 | 43.1% | 7.1% | -2.3% | -12.0% | PF, costs, DD, regime |
| BLEND mom+carry+trend + VT | 1.10 | 1.05 | 32.5% | 10.8% | -14.0% | +1.8% | PF, costs, DD, regime |
| BLEND mom+carry + VT | 1.04 | 1.00 | 35.1% | 4.3% | +3.6% | -0.5% | PF, costs, DD, regime |
| CARRY (funding) | 1.00 | 0.96 | 56.5% | -1.7% | -1.2% | -7.1% | PF, costs, DD, regime |
| CARRY + vol target | 1.00 | 0.96 | 51.7% | -1.2% | -1.3% | -2.2% | PF, costs, DD, regime |
| XS_REV (control) | killed on dev: median config -94% | | | | | | |

Live reference (VBreak4Live, same holdout gates, from GO_NO_GO.md): PF 1.198, PF 2x 1.136,
all four regimes positive, portfolio DD 34.9-37.4%.

## What was learned
- **Funding carry looked like the best idea on dev coins (Sharpe 1.44) and was worth nothing on unseen
  coins (PF 1.00).** It was the strongest overfit in the sweep.
- **Long-only trend with a BTC gate is the only family that is both profitable and low-drawdown
  on unseen coins** (PF 1.53, 2x costs 1.45, DD 19%). It fails only because it lost 14% in 2022.
  Returns are small (~10%/yr at ~12% average exposure).
- Every long-biased family lost money in 2022. The live strategy's short leg is why it passed that
  regime; nothing here replaces it.
- Momentum strategies earn high returns but with 60-80% drawdowns. They cannot meet a low-DD target.

## Checks
- Extra-delay test (TREND_GATED held one and two days later): PF 1.37-1.39, so the edge is not lookahead.
- Engine arithmetic re-computed with an independent loop: identical to machine precision.
- Survivorship: universe = coins listed today. This flatters long legs; results above are, if anything,
  optimistic for the long-only families.

## Costs model
0.05% fee + 0.05% slippage per side, actual funding events (longs pay positive funding).
Stress: 2x fee+slippage, and separately 2x funding.
