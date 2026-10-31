# Desk 15m / 30m limit-entry (maker) breakout: result

**Run 2026-09-28, executing `PREREGISTRATION_2026-09-28_desk_maker.md` (SHA-256 in every output). Seed 20260929. Runtime 30 s. Fill/exit logic checked on six synthetic price paths before the run (touch ≠ fill, trade-through fills, same-minute stop first, expiry, placement delay, fee arithmetic) — all matched.**

## Verdict

**Nothing validated. 0 of 128 combinations passed Stage 1**; every one failed G2 (PF < 1.15) and G3 (2x-cost PF < 1.05), 120 also G4. All 4 walk-forward groups failed. **The sealed quadrant was NOT opened** — still clean.

## Why: adverse selection, measured

| Group | Fill rate | Median PF | Best PF (2x) | Missed signals, if entered at market |
|---|---|---|---|---|
| long 15m retest | 41-50% | 0.79 | 0.89 (0.75) | +0.30 R |
| long 15m pullback | 68-78% | 0.84 | 0.89 (0.75) | +0.83 R |
| long 30m retest | 36-48% | 0.78 | 0.95 (0.84) | +0.37 R |
| long 30m pullback | 70-76% | 0.88 | 0.99 (0.88) | +1.01 R |
| short 15m retest | 45-55% | 0.89 | 0.96 (0.83) | +0.39 R |
| short 15m pullback | 68-80% | 0.95 | 1.06 (0.91) | +0.92 R |
| short 30m retest | 43-53% | 0.93 | 1.02 (0.90) | +0.55 R |
| short 30m pullback | 70-81% | 0.995 | 1.08 (0.94) | +1.16 R |

The last column is the whole story. **The signals a limit order misses are exactly the ones that run** — entered at market they average +0.3 to +1.2 R. **The ones that fill are the breakouts that fail back**, and those lose. Cheaper fees (maker) don't come close to paying for that selection. This is the outcome §10 named as the risk, and it is larger than expected: the market-entry version was roughly break-even (DESK15M_REPORT), the limit version is clearly worse.

(The missed-signal figure is flattering by construction — "price never pulled back" is itself future information — so it is not a strategy; it measures what the limit order gives away.)

Walk-forward: long 15m had no training fold clear PF >= 1.10; long 30m -32.9 R (0/6 positive), short 15m -17.1 R (2/6), short 30m -11.9 R (2/6).

## What this settles

- **Scalping this setup on 15m/30m is ruled out both ways:** market entries lose to fees, limit entries lose to adverse selection. Three pre-registered tests today and yesterday agree.
- For a manual desk the practical reading is the opposite of the usual advice: **on these breakouts, chasing with a market order is less bad than waiting for a pullback**, and neither is profitable.
- Still open: short breakout-with-flow on 1h, tracked forward from 2026-09-28 (`PREREGISTRATION_2026-09-28_short1h_forward.md`). The sealed quadrant remains unused.

## Files

`research/desk_maker_run.py`, `research/desk_data_1m.py`, `research/results/desk_maker_stage1.json` … `_stage4.json`, `user_data/logs/desk_maker_run.log`.
