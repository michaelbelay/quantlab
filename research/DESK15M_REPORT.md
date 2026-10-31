# Desk 15m / 30m research: result

**Run 2026-09-27, executing `PREREGISTRATION_2026-09-27_desk15m.md` (SHA-256 `adcf5149...0969`, recorded in every output file). Seed 20260927. Runtime 163 s.**

## Verdict

**Nothing validated. 0 of 192 combinations passed Stage 1, so Stages 2-4 had nothing to test.** The Signals panel stays empty.

**The sealed quadrant (holdout coins x the last 6 months) was never opened.** It is still clean data for a future test.

| Stage | Result |
|---|---|
| 1: dev coins x dev period | **0 / 192** pass. All 192 fail G2 (PF < 1.15) and G3 (PF at 2x costs < 1.05); 191 also fail G4 (profitable on fewer than 9 of 15 coins); 8 fail G1 (too few trades) |
| 2: walk-forward (per family x direction x timeframe) | 0 / 20 groups pass. 15 groups never had a training fold clear the PF >= 1.10 floor, so they traded nothing |
| 3: robustness | nothing to test |
| 4: sealed quadrant | **not opened** |

Only **1 of 192** combinations even broke even at base costs: `B|short|30m|N=48|k=2.5|s=1.5|r=1.5`, PF 1.0001, expectancy +0.0001 R, and it lost at 2x costs (PF 0.81).

## Best result per setup (base costs, dev coins x dev period)

| Setup | Best 15m PF | Best 30m PF |
|---|---|---|
| B breakout with flow, long | 0.75 | 0.99 |
| B breakout with flow, short | 0.88 | **1.00** |
| F failed breakout, long / short | 0.68 / 0.73 | 0.71 / 0.80 |
| P pullback in trend, long / short | 0.68 / 0.76 | 0.74 / 0.88 |
| L flush reversal, long / short | 0.71 / 0.99 (115 trades) | 0.90 / 0.93 |
| X crowding fade, long / short | 0.76 / 0.81 | 0.84 / 0.86 |

## Post-hoc diagnostic: edge before costs (NOT a gate)

`research/desk15m_gross_diag.py` re-ran all 192 combinations with **zero fees, slippage and funding** on the same dev data. The sealed quadrant was not touched. This cannot validate anything. Picking the best of each group is itself selection, so these numbers flatter.

- **112 of 192** combinations have positive expectancy before costs.
- The only meaningful gross edge is the **30m breakout with flow (B)**: long **+0.147 R** per trade (PF 1.26, 1,265 trades), short **+0.138 R** (PF 1.28, 1,121 trades). Next is the 15m short flush reversal (L), at +0.163 R, but on only 115 trades.
- Pullback (P), failed breakout (F) and crowding fade (X) are near zero even before costs. There's no edge to protect in those.

**Reading:** base costs of 0.14% round trip come to about **0.15 R per trade** at these stop sizes. That equals almost exactly the entire gross edge of the best setup. The breakout idea is real (it matches the 1h volatility-breakout result from earlier research), but at 30m **the market-order costs of trading it by hand consume all of it**. This is the same failure mode as every earlier high-frequency candidate in this project, and it matches the expectation written in §10 of the pre-registration, before the run.

## What this rules out, and what it doesn't

- **Ruled out:** any of these 5 setups traded at 15m/30m **with market (taker) orders**, on these coins, in this regime.
- **Not tested:**
  - **limit-order (maker) entries**, which would cut costs to about 0.04-0.07% round trip, but with fill risk and adverse selection
  - **1h / 4h** versions of the breakout-with-flow setup, where the same costs are a smaller share of each trade

  Either needs a **new pre-registration**. The sealed quadrant is still available for its final test.

## Files

- `research/results/desk15m_stage1.json` ... `_stage4.json`: every combination, its numbers and the gates it failed
- `research/results/desk15m_gross_diag.json`: the zero-cost diagnostic
- `user_data/logs/desk15m_run.log`
