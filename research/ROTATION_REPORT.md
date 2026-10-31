# Weekly relative-strength rotation: result

**Run 2026-09-29, executing `PREREGISTRATION_2026-09-28_rotation.md` (SHA-256 `1bd2aee3…df6d`) with `AMENDMENT_2026-09-29_rotation_v3.md` (`58d23680…a2004`), exchangeInfo snapshot `a808644a…`. Seed 20260930. Final audit (A7) passed 7/7 before the run and was re-checked by the run itself. Offline only; VBreak4Live and the live account untouched.**

## Verdict

**Neither hypothesis validates. Both fail at Stage 1: no variant of either passes gates G1-G4 + G6-G7, so neither has a candidate.** G5 (random baskets), Stage 3 and Stage 4 had nothing to test. Stage 2 (walk-forward of the selection procedure) also failed for both.

**Neither the holdout universe nor the sealed period was opened.**

| | H-LO long-only | H-LS long-short |
|---|---|---|
| Variants passing Stage 1 (excl. G5) | 0 / 8 | 0 / 8 |
| Candidate | none | none |
| Walk-forward | 0 / 8 folds positive; no fold's training data qualified any variant, so every fold held cash (OOS 0.0%; benchmark -88.7%) | 0 / 8 positive; OOS **-37.4%**. Only the first fold (2022-H1, trained on 2021) picked a variant — L=28 K=3 no filter, training Sharpe 0.96 at 2x — and it lost 37.4%; no later fold qualified |
| Holdout / sealed | not opened | not opened |

## Stage 1, every variant (dev universe x dev period, 273 weeks, base costs)

| Variant | Sharpe (2x) | CAGR | Max DD | Market benchmark (same L) |
|---|---|---|---|---|
| LO L=14 K=3 off | 0.13 (0.08) | -51.0% | 99.0% | Sharpe -0.06, CAGR -34.5%, DD 94.5% |
| LO L=14 K=3 on | -0.11 (-0.15) | -46.3% | 98.1% | |
| LO L=14 K=5 off | -0.02 (-0.08) | -47.1% | 98.6% | |
| LO L=14 K=5 on | -0.16 (-0.20) | -40.5% | 96.2% | |
| LO L=28 K=3 off | **0.48** (0.44) | -22.9% | 93.8% | Sharpe -0.06, CAGR -34.1%, DD 94.3% |
| LO L=28 K=3 on | 0.21 (0.18) | -26.9% | 97.5% | |
| LO L=28 K=5 off | 0.29 (0.26) | -25.4% | 91.2% | |
| LO L=28 K=5 on | -0.08 (-0.11) | -36.9% | 96.9% | |
| LS L=14 K=3 off | 0.00 (-0.10) | -21.1% | 90.6% | cash benchmark |
| LS L=14 K=3 on | -0.23 (-0.32) | -28.5% | 95.5% | |
| LS L=14 K=5 off | -0.02 (-0.16) | -11.5% | 72.1% | |
| LS L=14 K=5 on | -0.13 (-0.25) | -16.7% | 82.8% | |
| LS L=28 K=3 off | **0.57** (0.50) | **+15.6%** | 84.5% | |
| LS L=28 K=3 on | 0.31 (0.23) | -3.2% | 89.7% | |
| LS L=28 K=5 off | 0.48 (0.38) | +12.5% | 66.8% | |
| LS L=28 K=5 on | 0.09 (0.00) | -7.5% | 82.6% | |

Gates (§9.1): Sharpe >= 0.80 (2x >= 0.60), max DD <= 50% (H-LS <= 35%), positive in >= 3 of 4 regimes, and the §7.2 market/cash conditions. **Every variant fails G2, G3 and G6; all but one fail G7.**

## What the numbers say (descriptive; nothing here changes the verdict)

- **The market itself collapsed.** An independent recomputation outside the simulator confirms the benchmark: an equal-weight basket of the 40 most-traded crypto perpetuals, before costs, went 2021 +75.6%, 2022 -81.6%, 2023 +106.5%, 2024 +5.1%, 2025 -75.1%, 2026 (to March) -40.1% — about **-90% overall**, while BTC buy-and-hold gained +101% over the same span. Worst single week -47%. With dead coins included, "holding the altcoin market" was a disaster.
- **Long-only relative strength beat that market but still lost money:** the best variant (L=28 K=3) returned -22.9% a year vs the market's -34.1%, with a 93.8% drawdown. Picking the strongest alts didn't escape the alt collapse.
- **Long-short was regime-bound:** the best variant (L=28 K=3) made +348.6% in 2025-26 — shorting the weakest alts during their collapse — after losing 45.0% in 2022 and 44.7% in 2023-24. The walk-forward shows the consequence: the one fold where training data qualified it, it lost 37.4%.
- **28-day lookback beat 14-day in all 8 pairs; the BTC filter made every one of the 8 pairs worse** — the opposite of the §12 expectation that the filter variants had the best chance.
- The pre-registered expectation ("most likely: neither hypothesis validates") held.

**On the 2025-26 long-short number:** it is the kind of result pre-registration exists to stop us chasing. It was one regime out of four, found by looking; the walk-forward already shows the procedure could not have picked it in advance. The sealed quadrant stays unopened, so it remains available for a future, separately pre-registered test — but that test would need a reason other than this number.

## Files

- `research/rotation_run.py`, `rotation_data.py`, `rotation_audit2.py`
- `research/results/rotation_final_audit.json`, `rotation_results.json`, `rotation_stage1.json` … `rotation_stage4.json`, `rotation_audit2*.{json,csv}`
- `user_data/logs/rotation_run.log`
