# Pre-registration: PF-based in-fold selection

Declared 2026-09-21, before running `wf_pf.py`.

## Why a new rule is being tested

The walk-forward on the 140-coin universe scored 4/8 folds positive at portfolio
level. The diagnosis was not the candidates but the **selection statistic**: the
original rule ranks candidates by raw return over the training window, which
systematically prefers the highest-churn family. It picked `trend_resume|btc|long`
in 4 of 8 folds, and that candidate returned −27.0, −20.5, +20.4, −42.1, −16.6
portfolio OOS. The two folds that selected a `volatility_breakout_b4` variant
returned +65.1 and +35.8.

## The rule, stated completely

Inside each training window, over the same fixed candidate set:

1. **Eligibility floor.** A candidate must have **≥ 100 trades** in the training
   window. Below that it cannot rank at any PF. This is the project's existing
   anti-degenerate-solution principle (`tournament.py`: "the safest way to score
   well is to stop trading") applied to fold selection.
2. **Rank by profit factor** (gross wins / gross losses) over the training window.
3. **Tie-break by trade count**, more evidence preferred.
4. The winner is scored on the immediately following out-of-sample window, at
   both aggregate/pair and portfolio level (10 slots, stake = equity/10).

Nothing else changes: same folds, same candidate set, same universe, same dev
coins, same costs.

## Success criterion, fixed in advance

The rule is an improvement only if it beats raw-return selection on
**portfolio-level folds positive**, which is currently 4/8. Aggregate return is
explicitly not the criterion — it assumes capital the account does not have.

## Contamination disclosure

This is **not a clean test.** I have already seen the OOS results under
raw-return selection, and I know that PF ranks `volatility_breakout_b4` above
`trend_resume`. Choosing PF is therefore informed by knowledge of the answer.

The result below is **suggestive, not validating.** A clean test of this rule
requires applying it to data or candidates it has not seen — the spot track, a
different universe slice, or newly generated families. That test is the one that
would count, and it has not been run.
