# Opportunity engine on the 280 unseen coins: RESULT (2026-10-07)

Pre-registration: `PREREGISTRATION_2026-10-06_unseen.md`. Frozen hashes verified by `unseen_test.py` before any
data was read (playbook.json 9ec9d590…, common.py b96f2c04…). 280/280 coins used, 33 s. Raw: `unseen_results.json`.

## Primary: VOLSPIKE_DN → LONG 48h — **FAIL → 🔴**
| | dev coins, test 2025-26 | unseen coins (all history) |
|---|---|---|
| cases | 1,424 | 7,295 |
| avg net / trade | +0.385% | **−0.131%** |
| median | −1.586% | −2.167% |
| day t | +1.78 | −0.29 |
| random entries | −0.201% | −0.249% (edge +0.12 pp) |
Gates: avg > 0 ✕ · beats random by ≥ 0.10 pp ✓ · day t ≥ 2 ✕.

## Secondary (all 13, same frozen rules)
| Rule | dev badge | unseen avg | unseen day t | edge vs random |
|---|---|---|---|---|
| BRK_LO20 SHORT 48h | 🟠 | +0.455% | −3.65 | +0.59 |
| SQUEEZE SHORT 48h | 🟠 | −0.002% | +0.80 | +0.09 |
| FUND_DIV_UP LONG 24h | 🟠 | −0.237% | −3.37 | +0.06 |
| CROWD_LONG SHORT 24h | 🔴 | +0.404% | +0.87 | +0.56 |
| FUND_DIV_DN LONG 48h | 🔴 | +0.815% | −0.66 | +1.07 |
| other 8 | 🔴 | ≤ +0.11% | ≤ +0.08 | |
No rule reaches day t ≥ 2 on the unseen coins. BRK_LO20 repeats its dev pattern: positive average from crash
clusters, negative on a typical day.

## Decision
- VOLSPIKE_DN → 🔴 (as registered).
- Stricter than registered (Michael asked for a "brutal" scanner, 2026-10-07): a rule whose unseen result fails the
  same three gates is also shown as 🔴. This only removes trade signals, it never adds one. Result: **no rule is
  currently tradeable.** All 13 stay tracked by the forward scoreboard; a rule can come back only through
  forward evidence (`forward.py`, rule stated in README).
- The unseen coins are now spent for these 13 rules.
