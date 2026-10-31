# Pre-registration: forward tracking of short breakout-with-flow on 1h

**Written 2026-09-28, approved by Michael the same day ("yes" to: track short-1h forward on new data, keep the sealed quadrant for the maker-order test). LOCKED.**

## Why this exists

In `DESK1H4H_REPORT.md` the short 1h breakout-with-flow passed every Stage 1 gate but failed walk-forward (3/6 folds, +15.6 R, carried by the spring-2025 sell-off). The dev period has now been seen, so it can't be re-tested there. The sealed quadrant is reserved for the maker-order scalping test. **The only clean evidence left is data that doesn't exist yet.** This document fixes the rule today, so everything after today is out-of-sample.

## The rule (fixed; chosen on seen data — disclosed)

`B|short|1h|N=48|k=2.5|s=1.0|r=2.0`, exactly as implemented in `research/desk1h4h_run.py`:

- 1h bars (UTC), short when close < lowest low of the previous 48 bars, **and** bar volume >= 2.5x its prior 20-bar average, **and** taker-sell share >= 55%, **and** open interest up over the bar (5-min series, lagged 5 min).
- Entry at the next 15m open (market); stop 1.0 x ATR(14, 1h); target 2.0 x stop; time stop 24 bars; exit path walked on 15m bars, stop assumed first on a shared bar.
- Costs: 0.14% round trip base, 0.28% at 2x, plus real funding.

It was picked because it had the best Stage 1 result and was the walk-forward's own choice in 3 of 6 folds. That choice used seen data; it doesn't matter here, because the grade uses only data after the start date.

## Forward window

- **Starts 2026-09-28 00:00 UTC.** Signals before that time are never counted (the desk data ends 2026-09-25; the gap days are excluded to keep the start unambiguous).
- **Coins:** all 30 in `user_data/desk_data/universe.json` (dev and holdout alike — all of them are unseen after the start).
- **Not shown on the Signals panel** while tracking. It is graded from the Binance archive after the fact, so no one acts on it and there is no selection by the operator.

## Checkpoint (one evaluation, no peeking for decisions)

Evaluated once, at the first of: **150 closed trades**, or **2027-03-31**. Expected pace ~10 trades/week across 30 coins → ~150 by mid-January 2027. Interim counts may be reported (trade count only); interim results are not used for any decision.

## Pass criteria (all required)

1. >= 150 closed trades (if the 2027-03-31 date arrives first with fewer, the result is **inconclusive**, not a pass).
2. **PF >= 1.15** at base costs.
3. **PF >= 1.05 at 2x costs.**
4. **Positive expectancy in at least 60% of the complete calendar months** in the window.
5. **Beats random entry:** same exits, costs, coins and trade count, random entry times in the same window, 200 runs (seed 20260928); expectancy above the 95th percentile.

## Decision

- **Pass** → becomes a `validated` desk card, with the demotion rule from the desk pre-registrations (100 graded cards below 0 R removes it).
- **Fail or inconclusive** → rejected. No parameter change is re-tracked on the same window.

## Output

A grading script `research/short1h_forward_grade.py` (to be written before the checkpoint; it must reuse `desk1h4h_run.py`'s signal and simulation code unchanged) → `research/results/short1h_forward.json`.
