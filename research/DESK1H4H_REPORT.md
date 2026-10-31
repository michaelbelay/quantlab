# Desk 1h / 4h breakout-with-flow: result

**Run 2026-09-28, executing `PREREGISTRATION_2026-09-28_desk1h4h.md` (SHA-256 recorded in every output file). Seed 20260928. Runtime 60 s.**

## Verdict

**Nothing validated.** 6 of 64 combinations passed Stage 1; all 4 walk-forward groups failed Stage 2, so Stages 3-4 had nothing to test. The Signals panel stays empty.

**The sealed quadrant (holdout coins x 2026-03-26..09-25) was NOT opened.** It is still clean.

| Stage | Result |
|---|---|
| 1: dev coins x dev period | **6 / 64** pass — five `short|1h`, one `long|4h` |
| 2: walk-forward | **0 / 4** groups pass |
| 3: robustness | nothing to test |
| 4: sealed quadrant | **not opened** |

Stage 1 failures (a combo can fail several): G3 2x-cost PF 47, G4 coins 45, G2 PF 39, G1 trades 20, G5 random 1.

## The near miss: short breakout-with-flow on 1h

Five `short|1h` combinations passed every Stage 1 gate comfortably — the first result in the desk research to do so:

| Combo | Trades | PF | PF 2x cost | Exp. R | Coins + | Random p95 R |
|---|---|---|---|---|---|---|
| N=48 k=2.5 s=1.0 r=2.0 | 429 | **1.47** | **1.24** | +0.276 | 12/15 | 0.014 |
| N=20 k=2.5 s=1.0 r=2.0 | 553 | 1.35 | 1.14 | +0.214 | 12/15 | 0.001 |
| N=48 k=2.5 s=1.5 r=2.0 | 414 | 1.34 | 1.15 | +0.195 | 11/15 | 0.004 |
| N=48 k=2.5 s=1.0 r=1.5 | 439 | 1.31 | 1.07 | +0.166 | 12/15 | -0.012 |
| N=48 k=2.5 s=1.5 r=1.5 | 424 | 1.30 | 1.10 | +0.158 | 11/15 | 0.016 |

It then **failed walk-forward by one fold**: out-of-sample **+15.6 R total, but only 3 of 6 folds positive** (rule: 4).

| Test fold | Picked | OOS R | Trades |
|---|---|---|---|
| 2025-03..05 | N=48 k=2.5 s=1.0 r=2.0 | **+22.5** | 48 |
| 2025-05..07 | same | +4.3 | 42 |
| 2025-07..09 | same | -0.0 | 27 |
| 2025-09..11 | N=20 k=2.5 s=1.0 r=2.0 | +7.8 | 48 |
| 2025-11..2026-01 | N=20 k=2.5 s=1.5 r=1.5 | **-19.0** | 84 |
| 2026-01..03 | none cleared the training floor | 0 | 0 |

**Reading:** the total is carried by one fold (2025-03..05, the spring 2025 sell-off). Remove it and the rest sums to -6.9 R. That is the regime-dependence shape this project has seen before (the harvested families passed every static gate and died at walk-forward the same way). It is recorded as **rejected**, per §8 — no partial credit, no re-run with a looser fold rule.

## Other groups

| Group | Best PF (2x) | Median PF | Walk-forward |
|---|---|---|---|
| long 1h | 1.16 (0.97) | 0.99 | -14.1 R, 2/6 |
| long 4h | 2.01 (1.82) on **18 trades** | 1.24 | +7.9 R, 3/6 — two folds untradeable, 7-9 trades per fold |
| short 1h | 1.47 (1.24) | 1.18 | +15.6 R, 3/6 |
| short 4h | 1.18 (1.11) | 0.92 | -11.1 R, 1/6 |

4h is what §10 predicted: costs stop mattering but the sample is too small — folds of 7-16 trades cannot establish anything.

## Control: does the order flow add anything?

Same grid with the three flow filters removed (plain N-bar breakout), dev x dev, base costs. Not a candidate.

| Group | Control best PF | Control median PF | With flow, median PF |
|---|---|---|---|
| long 1h | 1.00 | 0.94 | 0.99 |
| long 4h | 1.13 | 1.08 | 1.24 |
| short 1h | 1.06 | 0.96 | **1.18** |
| short 4h | 1.16 | 1.08 | 0.92 |

On 1h the flow filters are what turn a losing breakout into a winning one (short median 0.96 -> 1.18). On 4h they mostly cut the sample.

## What this rules out, and what it doesn't

- **Ruled out (under this pre-registration):** breakout-with-flow on 1h/4h with taker orders as a desk card.
- **Not ruled out:** the short-1h effect may be real but regime-bound. The only clean way to find out is **new data** — it cannot be re-tested on the dev period, which has now been seen. Two honest routes, each needing its own pre-registration: (a) grade the exact rule forward on data after 2026-09-25 without showing it on the panel, or (b) spend the sealed quadrant on it — but that quadrant is also the holdout for the maker-order scalping test next.

## Files

- `research/desk1h4h_run.py`
- `research/results/desk1h4h_stage1.json` … `_stage4.json`, `desk1h4h_control.json`
- `user_data/logs/desk1h4h_run.log`
