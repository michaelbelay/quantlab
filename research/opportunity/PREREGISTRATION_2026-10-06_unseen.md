# Pre-registration: opportunity engine on the 280 unseen coins

Written 2026-10-06, **before** any unseen-coin data was read. Status: **RUN 2026-10-07 on Michael's go - primary FAIL, see UNSEEN_RESULT_2026-10-07.md.**

## Frozen inputs
- `research/opportunity/playbook.json` sha256 `9ec9d590e9fe899f4320e130f29209d5c8e1296f22dc398ff3b53c39b38397aa`
- `research/opportunity/common.py` sha256 `b96f2c0445b3d9feab7cce0f3a2cad4d0cd02a0bb444daf70c2c78c6006689c4`
- No rule, threshold, horizon, target or stop may change after this file is written.

## Data
`research/pipeline/oos_universe.json["kept"]` (280 coins), `user_data/oos_data/<SYM>USDT/{ohlcv_1h,funding}.feather`,
full history to data end. Same cooldown, costs, entry and same-bar rule as the dev build.
Random baseline: 300 random entries per coin, seed 20261006.

## Primary hypothesis (one test)
**VOLSPIKE_DN → LONG 48h** (target 1.491 sigma24, stop 1.167 sigma24).
Passes if, on the unseen coins: avg net > 0, beats random entries by ≥ 0.10 pp, day t ≥ 2.
- Pass → upgraded from 🟠 to 🟡 (its dev day t was 1.78, just under 2), next step = paper forward test (G6) with alerts logged.
- Fail → 🔴, removed from the alert list (shown under NO TRADE).

## Secondary (reported, no decision)
All other 12 conditions with the same frozen rules, to check that the 🔴 verdicts also hold on new coins.

## After this test
The unseen coins are spent for these 13 rules. Any redesign of a rule must be tested on new data
(forward alerts) rather than on these coins again.
