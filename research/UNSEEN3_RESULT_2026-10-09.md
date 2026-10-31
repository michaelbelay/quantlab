# Result: 3 incubator ideas on the 280 unseen coins, 2026-10-09

Pre-registration: `PREREGISTRATION_2026-10-09_unseen3.md` (hashes `unseen3/hashes.txt`). Run once, exit 0.
Output: `unseen3/result.json`, `unseen3/trades_*.parquet`, `unseen3/run.out`. 280 coins, 2021-01-01..2026-09-25.

| Idea | Trades / days | PF | PF 2x | Day avg | Day t | w/o best 3 days | Random pct | Verdict |
|---|---|---|---|---|---|---|---|---|
| F1 crash bounce | 1335 / 343 | 1.90 | 1.82 | +1.52% | 1.76 | +0.43% | 100 | 🔴 fail (t < 2.4) |
| Volume absorption | 3102 / 834 | 1.12 | 1.07 | +0.50% | 1.22 | +0.14% | 100 | 🔴 fail |
| Channel UP_HIVOL (602db68df71a) | 12399 / 307 | 1.28 | 1.20 | +1.20% | 3.58 | +1.06% | – | 🟡 pass |

Years (net, %-points): F1 +171/+620/+144/+968/+1162/+987 (positive every year). Absorption 2024 −152.
Channel +218/−64/+4222/+471/+1246/+3381.

## Checks after the run (not part of the pass rule, reported for honesty)
- Channel: UP_HIVOL days come in runs and trades overlap, so days are not independent. On weekly averages t = 0.66
  (69 weeks), monthly t = 0.40 (31 months, 58% positive). The daily t 3.58 overstates the evidence.
- Channel: 275 coins, 75% net positive, top 5 coins = 14% of net (not a few-coin effect). Median trade −0.15%,
  win rate 43%: profits come from a minority of large winners. Median 26 trades per entry day — far more than
  a 300 USDT account can hold.
- F1 failed the rule but is the most consistent: positive in all 6 years, beat every random draw
  (random median day avg −0.51%). It keeps incubating on live data.

## Status
Channel UP_HIVOL = 🟡 research lead by the pre-registered rule, with a weak-evidence warning (weekly t 0.66).
Next: 300 USDT simulation with realistic position limits; keeps incubating. No trading. Unseen coins are spent for
these 3 ideas.

## Note added 2026-10-09 afternoon: phantom trades in the channel row
About 4,600 of the 12,399 channel trades (engine-based) are fee-only "trades" on coins whose price was frozen
(open = high = low = close for hours, e.g. AIA after delisting/halt): ATR ~ 0 puts the 8-ATR stop at the entry and the
trade closes one bar later at about -0.15%. No real market existed. F1 and absorption are not affected (17 such
trades each = normal). Removing them only removes fee losses, so the channel 🟡 above cannot get worse; it was not
re-run (unseen coins spent). The data fix (DEAD filter) is in `cap300/channel_redesign.py`.

## Correction run 2026-10-09 evening: channel row without phantom trades (`unseen3/channel_dead_fix.py`)
Same trades, same pass rule, only the DEAD filter applied (hash `unseen3/channel_dead_fix.sha256`, output `.out`/`.json`).
The "before" line reproduces the table above exactly (t 3.58, weekly 0.66, monthly 0.40).

| Channel UP_HIVOL | Trades / days | PF | PF 2x | Day avg | Day t | w/o best 3 days | Weekly t | Monthly t | Rule |
|---|---|---|---|---|---|---|---|---|---|
| Before (as recorded) | 12399 / 307 | 1.28 | 1.20 | +1.20% | 3.58 | +1.06% | 0.66 | 0.40 | 🟡 pass |
| After (4,891 dead trades on 17 coins removed) | 7508 / 305 | 1.31 | 1.26 | +1.90% | 4.55 | +1.71% | 1.05 | 0.62 | 🟡 pass |

Years after (net %-points): 2021 +218, 2022 −64, 2023 +4250, 2024 +552, 2025 +1339, 2026 +3905.
Verdict unchanged: 🟡 by rule; the weak-evidence warning stays (weekly t 1.05, monthly t 0.62 — still far from 2).
The 300 USDT simulations were not affected on dev coins (0 dead trades there).
