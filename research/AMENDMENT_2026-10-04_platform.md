# Amendment 2026-10-04: research resumes as a platform

**Supersedes §1c-§1d of `PAUSE_NOTE_2026-09-29.md` (the pause on new strategy research).**
Decided by Michael on 2026-10-04 ("yes" to `PLATFORM_PLAN_2026-10-04.md`, stages S0-S2).

## What changes
- New strategy research is no longer paused. It continues as a **pipeline** with explicit,
  versioned gates (`research/registry/gates.yaml`) instead of one-off pre-registrations.
- Every strategy the system knows (adapters, library strategies, engine candidates, desk tests)
  is kept in one registry (`research/registry/platform.db`) with a lifecycle status and a reason.
  **Nothing is deleted; rejected strategies stay visible with the reason.**

## What does not change
- The live account: `config_live_mainnet.json`, `VBreak4Live.py`, keys, watchdog, pre-flight,
  halt 180 / abort 120 USDT. The live bot stays **paused**; resuming is Michael's action only.
- The locked research files listed in the pause note (§1c) are not edited. Importers read them.
- The short-1h forward tracking and its checkpoint rules (pause note §3) stay as written.
- **LIVE is never reached automatically.** Promotion to LIVE is a manual decision.

## Out-of-sample data for G4 (stage S4, 2026-10-04)
- Rule fixed in `research/pipeline/oos_data.py` before any return was computed: every USDT perpetual
  in the public archive (delisted included) minus the 140 engine coins, minus the 15 sealed desk
  coins, minus stablecoins; >= 90 days of bars and median daily volume >= 5M USDT.
  Result: **331 coins** (20 delisted, 80 with history from 2021), listed in `research/pipeline/oos_universe.json`.
- **The rotation test's sealed holdout universe is spent by this use:** 163 of the 331 coins belong to it.
  Rotation is closed (REJECTED, `ROTATION_REPORT.md`), so its seal no longer protects a live question.
  Stated here so nobody later treats those coins as unseen for a rotation test.
- The desk sealed quadrant (15 coins × 2026-03-26..2026-09-25) is untouched: those coins are excluded.

## Known contamination carried forward
- The 63 "holdout coins" have been used by at least seven sweeps (tournament, harvest, universe,
  gate, short-gate, btc-regime, cloud sweep). From now on they count as **development data**.
  Out-of-sample gates use new data: a time holdout, delisted coins, and coins listed after the
  last sweep (see the plan, §5).
- The funding-carry candidate (`CANDIDATE_REASONS_2026-09-29.md`, rank 1) was already tested in
  `cloud_sweep_2026-09-25`: holdout PF 1.00. It enters the registry as REJECTED with that reason.
