# Pre-registration: breakout with order flow on 1h / 4h (decision desk, round 2)

**Drafted 2026-09-27, before any 1h or 4h test has been run on the desk data. Status: DRAFT, awaiting Michael's approval.**
Nothing in this document may be changed after the first test runs. Anything this document does not restate is inherited unchanged from `PREREGISTRATION_2026-09-27_desk15m.md` (data, no-lookahead rules, splits, simulation, costs).

## 1. The question

Does the **breakout-with-flow** setup from round 1 survive taker costs when traded on **1h or 4h** bars? On 30m it had an edge before costs (about +0.14 R per trade), and costs took roughly 0.15 R per trade. On longer bars the stop is wider, so the same 0.14% round-trip cost is a smaller share of each trade.

## 2. Contamination disclosure: stricter than round 1

- **I have seen results for this family on the dev data.** Round 1 ran it on dev coins x dev period at 15m and 30m, both after costs and (post-hoc) before costs. 1h and 4h bars are built from the same 15m candles. **The dev quadrant is therefore not fresh for this family.** A pass at Stages 1-3 is weaker evidence than it looks.
- The reason for choosing this family and these timeframes is that result. It's selected, not neutral.
- **What stays clean: the sealed quadrant** (holdout coins x 2026-03-26 to 2026-09-25). Round 1 never opened it. **Stage 4 is the only part of this test on data nothing has seen, and the decision rests on it.** If Stage 4 runs, the quadrant is used up for this family.
- Earlier 1h research (volatility breakout, 2021-2026, overlapping coins) found that breakouts work at 1h. That is a prior, not evidence here: different rules, different exits, different holding period.

## 3. What is tested (fixed)

**One family, B (breakout with flow), long and short as separate candidates.**

| | Long (short is the mirror) |
|---|---|
| Trigger | the bar closes above the highest high of the previous *N* bars |
| Volume | bar volume >= *k* x the average of the previous 20 bars |
| Aggressive flow | aggressive-buy share of the bar's volume >= 55% |
| Open interest | OI higher at the bar's close than at its open (new positions during the breakout bar), using the same 5-min lag as round 1 |

*Changed from round 1:* the OI window is now **the signal bar itself** rather than "the last hour", because a fixed hour means something different on a 4h bar.

**Timeframes:** 1h and 4h, resampled from the 15m archive (first open, max high, min low, last close, summed volume and taker-buy volume).

**Grid:**

| Parameter | Values |
|---|---|
| N (breakout lookback) | 20, 48 |
| k (volume multiple) | 1.5, 2.5 |
| s (stop, x ATR(14) of the timeframe) | 1.0, 1.5 |
| r (target, x stop distance) | 1.5, 2.5 |
| T (time stop) | **fixed**: 24 bars on 1h (1 day), 18 bars on 4h (3 days) |

4 entry combos x 4 exit combos x 2 directions x 2 timeframes = **64 combinations exactly**. That is the whole search.

## 4. Simulation (as round 1, except the human-delay test)

- Signal on bar *t*'s close. Entry at the open of bar *t+1* with taker fee plus slippage. The stop is assumed hit first when a bar touches both levels. Gaps fill at the open. The time stop exits at the next bar's open. One open trade per coin per combination. Results are in R.
- **Costs:**
  - base: 0.05% fee + 0.02% slippage per side, 0.14% round trip, plus real funding
  - 2x: 0.28% round trip
- **Human delay (G7), redefined in real time:** entry at the open of the **15m bar starting 30 minutes after the signal bar closes**, with stop and target measured from that price. A one-bar delay would mean 1 or 4 hours, which isn't how you'd actually react.

## 5. Gates

Every gate from round 1 applies. Only the trade-count floors change, because 1h and 4h fire less often. Failing any gate rejects the combination.

| Gate | 1h | 4h |
|---|---|---|
| G1 trades, dev coins x dev period | >= 150, on >= 10 of 15 coins | **>= 80**, on >= 10 of 15 coins |
| G2 PF, base costs | >= 1.15 | >= 1.15 |
| G3 PF, 2x costs | >= 1.05 | >= 1.05 |
| G4 coins with positive expectancy | >= 9 of 15 | >= 9 of 15 |
| G5 beats random entry | > 95th percentile of 200 runs | same |
| Stage 2 walk-forward | total out-of-sample R > 0 and >= 4 of 6 folds positive | same |
| Walk-forward training floor | >= 30 trades and PF >= 1.10 | **>= 15 trades** and PF >= 1.10 |
| G6 neighbours | each one-step neighbour PF > 1.0 | same |
| G7 human delay (30 min) | PF > 1.0 | same |
| G8 without the best coin | PF >= 1.10 | same |
| G9 sealed-quadrant trades | >= 50 | **>= 30** |
| G10 sealed PF, base costs | >= 1.10 | >= 1.10 |
| G11 sealed PF, 2x costs | >= 1.00 | >= 1.00 |

- Walk-forward folds are the same 6 as round 1 (train 6 months, test 2 months, covering 2025-03 to 2026-03). Selection is by training PF within each direction x timeframe group of 16 combinations.
- **Stage 4:** at most 5 combinations, ranked by walk-forward out-of-sample R, opened once.

**Why the 4h floors are lower, and what it costs:** 4h breakouts fire rarely. A floor of 150 would reject 4h on count alone, whatever the edge. The lower floors mean a 4h pass rests on fewer trades, so its estimate is noisier. That is accepted here and will be stated next to any 4h card.

## 6. Decision rule

> **`validated` = passes all 11 gates across Stages 1-4.** Anything else is rejected and never reaches the panel. No loosening, no re-runs with other thresholds.

**Card rules for a validated setup:**

- expiry of 2 hours (1h) or 4 hours (4h) after the signal bar closes
- stop and target taken from the setup
- **demotion** after 100 graded cards if realised expectancy after base costs is below 0 R. At 4h that may take months, and the card shows its graded count until then.

## 7. What I expect (before running)

Rough cost per trade in R: at 1h, 0.14% against a stop of about 1-1.5 x an hourly ATR of about 0.8-1.2% is **roughly 0.1-0.15 R**; at 4h, **roughly 0.05 R**.

- **1h:** likely still marginal. The saving over 30m is smaller than it sounds.
- **4h:** the best chance on cost, but the risk moves to **G1/G9 trade counts**, the walk-forward training floor, and noise.

**Most likely outcome: nothing passes. If anything does, it's a 4h long.** Recorded now, not to lower any gate.

## 8. Outputs

- `research/desk1h4h_run.py`: one run, seed 20260927.
- `research/results/desk1h4h_stage1.json` ... `_stage4.json`.
- `research/DESK1H4H_REPORT.md`.
- `user_data/desk/setups.json`, only if something validates.
