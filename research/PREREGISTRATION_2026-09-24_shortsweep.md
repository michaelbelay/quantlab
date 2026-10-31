# Pre-registration — second short-side sweep

**Written 2026-09-24, before the sweep was run.**

## Why the rule is fixed first

I have already seen the first short sweep. I know `bear_trend_continuation` reached
a 2×-cost PF of **0.990** and that its scores improved monotonically with
`adx_max` 25 → 35 → 45, and I know `volume_breakdown` topped out at 0.963. I also
recorded at the time that the "best" combos were picked by scanning a grid that
**included holdout columns**, so holdout is already partly contaminated for those
two families.

Knowing which direction the numbers moved is exactly the state in which a
threshold gets nudged to let a favourite through. So the rule is written now.

## What is being searched

The 9 short-only families get the parameter and exit-geometry sweep they never
had — the equivalent of the bars=2/3/4/6 sweep that made the long side work:

| axis | values |
|---|---|
| family | all 9 short-only families |
| stop distance | `stop_atr` 2.0, 3.0, 4.0 |
| holding period | `max_bars` 200, 400, 800 |
| family parameter | each family's own, swept around its default |
| filters | `nofilt`, `btc`, `btc+vol` |

Screening runs on the **70 dev coins**. Only survivors go to the holdout.

## Stage 1 — screening gate, on dev coins

A combination advances only if **all** hold:

1. **≥ 100 trades/year** across the dev set. The project's anti-degenerate floor:
   the easiest way to score well is to stop trading.
2. **PF ≥ 1.10** at normal costs.
3. **PF ≥ 1.05 at 2× costs.** Deliberately stricter than "survives" — the first
   sweep died here and a high-churn short leg will die here again.
4. **Positive in bear2022 AND recent2025_26.** A short book that cannot make money
   in the one sustained bear, or cannot make it in the regime we are actually
   trading, is not worth carrying.

## Stage 2 — holdout gauntlet, on the 63 unseen coins

Survivors face the same gates the long side had to clear:

5. **2× costs PF ≥ 1.10**
6. **2× slippage PF > 1.00** and **2× funding PF > 1.00**
7. **Positive in all four regimes**
8. **Walk-forward**: OOS portfolio sum > 0 and ≥ 4 of 8 folds positive
9. **Portfolio-20 max drawdown ≤ 40%**

## What a pass would and would not mean

A candidate clearing stages 1 and 2 is a **standalone short strategy worth a
parallel paper-trade on its own port**. It is explicitly **not** a change to
`VBreak4Live`, whose short leg is already validated as a hedge component and is
not in question here.

## Decision rule

> **Report every combination that clears stage 1, ranked. Promote to stage 2 only
> those that clear it. Adopt nothing automatically.** A stage-2 pass earns a
> recommendation and a paper-trade slot, never a live change.

If nothing clears stage 1, the correct output is "nothing cleared, here is how
close the best got" — not a relaxed threshold.

## Contamination disclosure

- `bear_trend_continuation` and `volume_breakdown` have had holdout columns
  scanned before. A holdout pass for **those two specifically** is weaker than it
  looks and must be labelled so in the report.
- The other 7 families were screened on dev only in the first sweep, so their
  holdout remains comparatively clean.
- No threshold in this document may be changed after seeing results. If one turns
  out to be wrong, that is a finding for the next pre-registration, not this run.
