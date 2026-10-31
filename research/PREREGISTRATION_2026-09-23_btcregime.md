# Pre-registration — dropping `btc_regime` from the live spec

**Written 2026-09-23, before the holdout gauntlet was run.**

## Why this document exists

I have already seen an in-sample result for this change: on the 127-pair live
universe it produced +32% trades, net +5,317 vs +4,637, max drawdown 12.5% vs
14.1%, Sortino 3.35 vs 2.83. That is encouraging and it is exactly the state in
which a decision rule gets quietly bent to fit the answer.

So the rule is fixed here, first. The project has been burned before by judging a
candidate after seeing its numbers: on 2026-09-21 four harvested families cleared
coin holdout, 2× costs and parameter neighbours, were called validated, and had
to be retracted one turn later when walk-forward killed them.

## The comparison

| | filters | everything else |
|---|---|---|
| **LIVE** | `btc_regime`, `volume` | identical |
| **CANDIDATE** | `volume` only | identical |

`volatility_breakout`, bars=4, atr_mult=2.0, direction=both, 1× leverage,
ATR stop 2.0, no take-profit, instant entry. Only the filter list differs.

**Test set: the 63 holdout coins** from `split_140.json` — the rule-based
alternating-market-cap-rank split fixed before any of this work.

## Hard gates — failing any one rejects the candidate outright

1. **2× costs**: profit factor ≥ **1.10**. (The live spec scored 1.128–1.136 on
   this gate; a +32%-churn variant is exactly the profile doubled costs kill.)
2. **2× funding**: profit factor > **1.00**.
3. **2× slippage**: profit factor > **1.00**.
4. **Regimes**: positive in **all four** of bull2021, bear2022, recovery2023_24,
   recent2025_26. The live spec achieves this and it is the reason it was chosen.
5. **Walk-forward**: OOS portfolio sum > 0 **and** folds positive ≥ **4 of 8**.

## Superiority tests — must beat LIVE on all three

Passing the gates only makes the candidate viable. Replacing a running live
strategy requires it to be *better*, not merely acceptable:

6. **Portfolio-20 return** ≥ LIVE's.
7. **Portfolio-20 max drawdown** ≤ LIVE's.
8. **Walk-forward OOS portfolio sum** ≥ LIVE's.

## Degradation accepted in advance

Profit factor and per-trade expectancy **are expected to be lower** — that is the
known shape of this trade (more trades, each worth less). Lower PF and expectancy
alone do **not** reject the candidate, provided gates 1–5 pass and superiority
tests 6–8 all hold.

## Decision rule

> **Adopt only if all five hard gates pass AND all three superiority tests pass.**
> Any other outcome: reject, keep `VBreak4Live` exactly as it is.

No partial credit, no "close enough", no re-running with adjusted thresholds. If
the candidate fails, the report says why and the live configuration does not move.

## Contamination disclosure

- The 63 holdout coins have been scored before — the live spec's own validation
  used them. This is therefore **not pristine data**; it is the designated
  holdout being used a second time for a different question. Treat a marginal
  pass as weaker than it looks.
- The in-sample result that motivated this test was computed on the 127-pair live
  universe, which **includes** dev coins. It is not evidence and is not cited in
  the decision.
- No parameter will be tuned during this run. One candidate, one live control,
  the gates above, once.
