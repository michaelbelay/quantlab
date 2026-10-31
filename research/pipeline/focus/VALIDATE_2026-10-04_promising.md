# Validation run: every PROMISING strategy + the live strategy on the 280 unseen coins

**Pre-registered 2026-10-04, before any of these strategies was run on the out-of-sample coins.**

## Why
The registry holds 11 PROMISING strategies and 1 VALIDATED (VBreak4Both, legacy evidence only). None has been
tested on the 280 coins no research has used (`oos_universe.json`). That test decides whether any of them
is real. Their configurations were all fixed earlier; nothing is re-tuned here.

## Strategies (configurations frozen as recorded)
**A. 1h engine strategies** (spec as in `universe_run.py`: trend_mode with, ATR 2.0 stop, no take-profit,
exit on the opposite signal, 400-bar time exit, leverage 1):
1. VBreak4Both — volatility_breakout bars=4 atr_mult=2.0, btc_regime+volume, both  (the live strategy's rules)
2. volatility_breakout bars=4 atr 2.0 · btc_regime · both
3. volatility_breakout bars=4 atr 2.0 · btc_regime · long
4. volatility_breakout bars=4 atr 2.0 · btc_regime+volume · long
5. volatility_breakout bars=2 atr 2.0 · btc_regime · long
6. volatility_breakout bars=2 atr 2.0 · btc_regime+volume · long
7. trend_resume · no filter · long
8. trend_resume · not_flat · long

**B. Daily portfolio strategies** (cloud sweep engine and parameters, `strats.py` / `overlay.py`):
9. TREND_GATED — ts_trend long-only lb=20, target vol 0.30, method ret, daily; held only while BTC > 50-day SMA
10. XS_MOM_LONG+VT — xs_mom lb=14 skip=1 n=5 every=14 long-only, BTC>100-day SMA filter, vol-targeted 20%
11. BLEND(MOM,CARRY,TREND)+VT — the cloud sweep's equal-risk blend

Not included: SpotVolBreak (spot; the out-of-sample set is futures).

## Data
Out-of-sample: the 280 crypto coins in `research/pipeline/oos_universe.json`, 1h futures OHLCV + funding,
2021-01 → 2026-09. BTC itself (development data) is used only as the regime gate, as in the original rules.
Costs: fee 0.05% + slippage 0.05% per side; 2x costs reported.

## Pass bar on the unseen coins (all required)
- A: G4 as in gates v1: PF ≥ 1.10, expectancy ≥ 60% of development, random-entry ≥ p95; plus G5 ≥ 5/8 folds;
  plus PF ≥ 1.05 at 2x costs and drawdown ≤ 40% on the live construction (20 slots, ≤ 10 same direction).
- B: PF ≥ 1.10, PF at 2x costs ≥ 1.05, max drawdown ≤ 40%, ≥ 3 of 4 regimes (2021, 2022, 2023-24, 2025-26) positive.

## Decision rule
- Pass → VALIDATED on clean data → eligible for a **paper** forward test (S5). Never live from this run.
- Fail → REJECTED with the out-of-sample numbers as the reason (VBreak4Both keeps its live status; the result
  is recorded against it and reported to Michael for his decision).

---

## RESULT, part B (run 2026-10-04, `validate_daily.py`, 280 unseen coins + BTC as gate only)

Builder check first: TREND_GATED re-run on the original 70 development coins with the new per-coin daily builder
gave PF 1.683 / 2x 1.595 / total +94.5% / DD 17.7% vs the recorded 1.678 / 1.590 / +93.7% / 17.7%. Faithful.

| Strategy | PF | 2x costs | Max DD | CAGR | 2021 | 2022 | 2023-24 | 2025-26 | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| TREND_GATED | **1.38** | **1.32** | **19.7%** | 6.9% | +20.9% | −9.6% | +36.3% | −2.9% | FAIL (2/4 regimes) |
| XS_MOM_LONG+VT | 0.98 | 0.95 | 44.4% | −4.1% | −0.6% | −19.6% | +20.0% | −16.9% | FAIL |
| BLEND(MOM,CARRY,TREND)+VT | 1.00 | 0.96 | 44.3% | −2.0% | +28.9% | −20.0% | +30.1% | −33.6% | FAIL |

**Robustness of the TREND_GATED result (evaluation, not selection):** all 36 settings of the cloud sweep's own grid run on
the unseen coins (`validate_trend_gated_grid_oos.csv`): PF > 1 in 35/36, PF ≥ 1.10 in 30/36, 2x-cost PF ≥ 1.05 in 31/36,
drawdown ≤ 40% in 36/36 (median 19.9%), median CAGR 2.3%. **2022 positive in 0/36, 2025-26 positive in 0/36.**

**Reading:** TREND_GATED is the first strategy in the project whose edge transfers to coins no research touched, robustly across
its whole parameter neighbourhood and with low drawdown. It is a bull-market long trend edge: it earns in 2021 and 2023-24, is
mostly flat in 2022 (BTC gate) and loses modestly in 2025-26. Per the pre-set rule it is **not validated** (regimes 2/4).

## RESULT, part A (batch 17, 8 strategies on 133 development + 280 unseen coins): 0 validated

| Strategy | Dev PF | Unseen PF | Unseen 2x | Expectancy kept | Live-construction on unseen: return / DD | Folds |
|---|---|---|---|---|---|---|
| **VBreak4Both (live rules)** | 1.27 | **1.07** | 1.02 | 29% | **−48% / 68%** | 4/8 |
| vb4 · btc · both | 1.27 | 1.07 | 1.03 | 33% | −45% / 68% | 4/8 |
| vb4 · btc · long | 1.52 | 0.91 | 0.87 | <0 | −74% / 80% | 4/8 |
| vb4 · btc+vol · long | 1.55 | 0.92 | 0.88 | <0 | −72% / 80% | 4/8 |
| vb2 · btc · long | 1.40 | 0.94 | 0.89 | <0 | −61% / 80% | 5/8 |
| vb2 · btc+vol · long | 1.41 | 0.94 | 0.89 | <0 | −66% / 80% | 5/8 |
| trend_resume · long | 1.11 | 0.95 | 0.89 | <0 | −34% / 74% | 3/8 |
| trend_resume · not_flat · long | 1.12 | 0.95 | 0.89 | <0 | +15% / 70% | 3/8 |

VBreak4Both's two-sided version keeps a small edge on unseen coins (PF 1.07, random-entry p99, bear 2022 strongly positive)
but loses money in the live portfolio construction there (−48%, 68% DD) and only 29% of its development expectancy survives.
The long-only breakout variants lose on unseen coins. Recorded for Michael's decision on the live strategy; nothing changed.
