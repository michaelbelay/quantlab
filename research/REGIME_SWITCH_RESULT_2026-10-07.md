# Result: regime-switching book, 2026-10-07 — 🔴 (test A failed, test B not run)

Rules: `PREREGISTRATION_2026-10-07_regime_switch.md`. Hashes (plan, script, then fit choice before the test window was
read): `regime_switch/hashes.txt`. Script `regime_switch.py`; outputs `regime_switch/` (fit_cells.csv, choice.json,
testA.json).

## Fit (2021-01..2023-12, 284 candidates × 4 BTC market types)
- 1110 cells had ≥ 100 trades; 31 had day-weighted t ≥ 3, 15 of those also PF ≥ 1.15, **2 passed every fit rule**.
  With 1110 cells, ~1.5 would pass t ≥ 3 by luck alone, so 2 is about what noise gives.
- Chosen:
  - `UP_LOVOL` (BTC trending up, calm): `streak_exhaustion · volume · long` (9ef3c32f80d4): fit 4271 trades,
    PF 1.19, t 3.1.
  - `UP_HIVOL` (BTC trending up, wild): `channel · not_flat · long` (602db68df71a): fit 1349 trades, PF 1.61,
    t 4.0. Note: +188 in 2021-22, +2416 in 2023, so mostly one year.
  - `DN_LOVOL` and `DN_HIVOL` (BTC trending down): **no strategy in the pool qualified, so cash.**
- 2/4 types filled, so the test continued (the stop rule needed < 2).

## Test A (133 development coins, entries 2024-01-01..2026-09-18)
| Check | Result | Needed | Pass |
|---|---|---|---|
| A1 PF / PF at 2× costs | 0.99 / 0.92 | ≥ 1.10 / ≥ 1.00 | ✗ |
| A2 day-weighted t | −0.17 | ≥ 2 | ✗ |
| A3 years positive | 2024 −2003, 2025 −1864, 2026 +3312 → 1/3 | ≥ 2/3 | ✗ |
| A4 switch vs no switch (P&L per day) | −0.56 vs −4.91 | higher | ✓ |
| A5 vs random switch (1000, 30-day blocks) | 79th percentile (random median −3211) | ≥ 95th | ✗ |

Book total −554 on 13,243 trades. Per type: UP_LOVOL −2938, UP_HIVOL +2383.

**Verdict 🔴.** Test B on the unseen coins is not run (§5: only if A passes). No re-run with other settings (§6).

## What it means, plainly
- The idea is not wrong: switching **did** cut losses a lot (−554 vs −4867 when the same two strategies run all the
  time), and the real switch beat 79% of random switches. Knowing the market type helps a little.
- But our pool has **no strategy that makes money after costs in any market type** once the period is new:
  - the calm-uptrend pick lost in the test;
  - nothing at all qualified for downtrends.

  A switch can only pick from what exists. Switching between losing strategies loses less, but it still loses.
- The one cell that stayed positive (`channel · not_flat · long` in wild uptrends, +2383) is an observation after the
  fact, not a result; acting on it would be choosing by looking. If wanted, it needs its own pre-registration on new
  data (forward, or unseen coins).
- What would be needed for the switching idea to work: strategies built **for** one market type (especially for
  downtrends: shorts, cash), rather than picking from 284 rules made to work everywhere.
