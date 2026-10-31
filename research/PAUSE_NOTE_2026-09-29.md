# Pause note — decision desk research

**Dated 2026-09-29. Revision 3 (revision 1 SHA-256 `3e8a3713…dd5d8`; revision 2 `c95905b5…ebada1c`). Revision 2 added, on Michael's review: disqualifier list, market context, failed priors, closed outcome ladder, automatic confirmation. Revision 3 applied edits E1-E6: pre-authorisation of the sealed-quadrant spend stated, revision 1's decision point withdrawn, confirmation bar aligned to the forward bar except the justified trade floor, pre-grade data audit with an explicit no-automatic-voiding default. Status: APPROVED by Michael on 2026-09-29 ("yes approved"), content identical to revision 3 as reviewed (SHA-256 before this status line was changed: `3685ac34…4a4f38`). IN EFFECT.**

## 1. What is paused, and why

**New strategy research on the desk is paused.** Four pre-registrations, testing five hypotheses, have run; none validated:

| # | Pre-registration | Hypothesis | Report | Result, and why |
|---|---|---|---|---|
| 1 | `PREREGISTRATION_2026-09-27_desk15m.md` | 15m/30m setups, market entries (192 combos) | `DESK15M_REPORT.md` | 0 pass — the only gross edge (30m breakout, ~+0.14 R/trade) was eaten by taker costs (~0.15 R/trade) |
| 2 | `PREREGISTRATION_2026-09-28_desk1h4h.md` | 1h/4h breakout-with-flow (64) | `DESK1H4H_REPORT.md` | 0 pass — short-1h passed Stage 1, failed walk-forward 3/6 folds; +15.6 R carried by one sell-off fold (+22.5 R; the rest -6.9 R) |
| 3 | `PREREGISTRATION_2026-09-28_desk_maker.md` | 15m/30m breakout, limit entries (128) | `DESK_MAKER_REPORT.md` | 0 pass — adverse selection: unfilled signals averaged +0.3 to +1.2 R at market; filled ones lost |
| 4a | `PREREGISTRATION_2026-09-28_rotation.md` + `AMENDMENT_2026-09-29_rotation_v3.md` | Weekly rotation, long-only (8) | `ROTATION_REPORT.md` | 0 pass — beat a collapsing market (-22.9%/yr vs -34.1%/yr) but lost money with >90% drawdowns; walk-forward: no variant qualified in any fold |
| 4b | same | Weekly rotation, long-short (8) | `ROTATION_REPORT.md` | 0 pass — best variant's return came from 2025-26 (+348.6%) after -45.0% (2022) and -44.7% (2023-24); walk-forward -37.4%, 0/8 folds positive |

Walk-forward was a stage inside tests 2, 3 and 4, not a separate test.

### 1a. Market context (kept with the results)

Recomputed independently of the rotation simulator (equal weight of the 40 most-traded crypto USDT perpetuals, point-in-time eligibility, dead coins included, before costs; dev universe, 2021-03 to 2026-03):

| 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (to March) | Whole span | BTC buy-and-hold, same span |
|---|---|---|---|---|---|---|---|
| +75.6% | **-81.6%** | +106.5% | +5.1% | **-75.1%** | -40.1% | **about -90%** | **+101.3%** |

Worst single week -47.2%, best +33.1%. After costs and funding, the benchmark as simulated: CAGR -34.1%/yr, max drawdown 94.3%. Every result in tests 4a/4b must be read against this: "holding the altcoin market" lost almost everything over the period.

### 1b. Recorded findings (kept, not dropped)

- **Failed prior — BTC regime filter.** The rotation pre-registration (§12) predicted the filter variants had the best chance. **The filter made every one of the 8 variant pairs worse.**
- **Finding with no written prior — lookback.** No prior was written on lookback length. **The 28-day lookback beat the 14-day in all 8 pairs.** It is recorded as an observation from a failed test, not as a validated parameter.

### 1c. The boundary of the pause

**Not allowed during the pause:**
- any new strategy backtest, and any re-run of tests 1-4 with different settings, universe, costs or gates;
- opening either sealed data set — **with one exception: the confirmation in §3.4, pre-authorised on 2026-09-29, and nothing else**;
- any change to VBreak4Live, VBreak4Both, any old-bot config, credential, bot, or the live account;
- any change to code a locked test depends on: `research/desk15m_run.py`, `desk1h4h_run.py`, `desk_maker_run.py`, `rotation_run.py`, `rotation_data.py`, `desk_data.py`, `desk_data_1m.py`, and `short1h_forward_grade.py` once its hash is recorded. If a defect is found in any of them, it is recorded and reported to Michael; it is not silently fixed.

**Allowed:** using the desk for charts and context; fixing bugs **outside** the files above (desk UI, control plane, data display); the forward-data download and the single grading run in §3.

**Short-1h is not shown anywhere on the desk while it is being tracked.** The Signals panel stays empty.

**Unchanged and untouched:** the live account is stopped (`user_data/8101.disabled` present, `initial_state: "stopped"`). No bot runs.

**Still sealed:**
- desk sealed quadrant — holdout coins (ETH, SOL, ENA, SUI, RARE, TAO, FIL, LTC, 1000PEPE, QNT, DASH, ARK, AAVE, SAGA, FET) x 2026-03-26..2026-09-25;
- rotation holdout universe, and the rotation sealed period 2026-03-26..2026-09-25.

### 1d. What ends the pause: the definition of "a new reason"

The pause ends only when Michael approves a **dated reason file** (`research/REASON_<date>.md`) written **before** any test is drafted. The file must name which qualifying category it belongs to and answer the bar question in writing. Claude checks the file against this section and states any objection in writing before anything proceeds.

**Not a reason (disqualifiers):**
1. a number produced by any of tests 1-4 or by the short-1h tracking, whatever its size;
2. a favourable regime, current or recent ("the market is trending now", "alts are recovering");
3. a parameter, lookback, filter or coin that won once, in one regime or one sample (this includes the 28-day lookback in §1b and the 2025-26 long-short result).

**A reason (it must be at least one of these):**
- **a new mechanism with a stated cause:** why the edge should exist, stated before any data is looked at, and not derived from these results;
- **a new dataset that changes what can be measured:** e.g. order-book depth or liquidation data that none of tests 1-4 could see;
- **a pre-registered test that could falsify a recorded finding**, including the findings in §1b.

**The bar, applied to every reason:** *would it still be worth running if the last five had all been profitable?* If the honest answer is no — if the reason only exists because the last five failed — it does not qualify.

## 2. What is still running

Only the short-1h forward tracking, per `PREREGISTRATION_2026-09-28_short1h_forward.md` (SHA-256 `9bb35e11…c0be812`, locked 2026-09-28).

**As of this note, no forward trade has been graded or could have been:** the grading script `research/short1h_forward_grade.py` does not exist; there is no result file; and the latest price bar in any local data file is **2026-09-25 23:59 UTC** (latest funding record 2026-09-26 20:00) — before the forward window opens on 2026-09-28. Checked 2026-09-29.

## 3. Short-1h forward tracking — every rule decided before any data is graded

### 3.1 The rule being tracked (unchanged)
`B|short|1h|N=48|k=2.5|s=1.0|r=2.0` exactly as in `desk1h4h_run.py`; all 30 desk coins; signals from **2026-09-28 00:00 UTC**; base costs 0.14% round trip, 2x = 0.28%, real funding.

### 3.2 Checkpoint (unchanged)
One evaluation, at the first of **150 closed trades** or **2027-03-31**. Expected pace about 10 trades/week, so roughly mid-January 2027 — the date is an estimate, the trade count is the trigger.

### 3.3 Pass criteria (inherited unchanged; all required)
1. >= 150 closed trades (reaching 2027-03-31 with fewer = **INCONCLUSIVE**, never a pass).
2. PF >= 1.15 at base costs.
3. PF >= 1.05 at 2x costs.
4. Positive expectancy in >= 60% of **complete** calendar months in the window.
5. Expectancy above the 95th percentile of 200 random-entry runs (seed 20260928; same exits, costs, coins, trade count, window).

**One wording change, marked:** the locked document says interim trade counts "may be reported". This note makes it narrower: **no interim result of any kind is computed; an interim trade count is produced only if Michael asks, and shows the count only.**

### 3.4 Interpretation rule and outcome ladder

**This section replaces the locked document's "Decision" section ("Pass → becomes a validated desk card").** Why a pass can't be taken at face value: the rule was chosen by looking (best of 64 on dev data), it failed walk-forward (3/6 folds, carried by one sell-off), and ~4 months of forward data is one market regime.

**Concentration check (added; a sixth condition — it narrows what counts as a pass, it does not change criteria 1-5):**
`concentration = (total R of the single calendar month with the largest total R) / (total R over the whole window)`, counting **every** calendar month that contains a closed trade, **including** the partial first and last months (unlike criterion 4). If `concentration > 0.50`, the outcome is **PASS-CONCENTRATED**. Evaluated only when criteria 1-5 all pass (so total R is positive).

**Confirmation test — fully specified now, runs automatically, no further decision:**
- **Trigger:** *Pre-authorised by Michael on 2026-09-29: on a forward PASS, the desk sealed quadrant is spent on this confirmation with no further decision. This replaces revision 1's decision point ("eligible for one confirmation test, only if a new pre-registration is decided on"), which is withdrawn.* It runs **immediately and automatically** after the forward grade returns **PASS**, in the same grading run. It does not run on any other outcome. No new pre-registration is written; this specification is the pre-registration and cannot be changed after the forward result is known.
- **Rule:** the same rule as §3.1, unchanged.
- **Data:** the **desk sealed quadrant** — the 15 holdout coins listed in §1c x 2026-03-26 00:00 .. 2026-09-25 23:59 UTC; 1h bars resampled from the 15m archive, exits walked on 15m bars, costs and funding exactly as in `desk1h4h_run.py`. Opened **once**.
- **Gates (all required):** (i) >= 50 closed trades; (ii) PF >= 1.15 at base costs; (iii) PF >= 1.05 at 2x costs; (iv) positive expectancy in >= 60% of complete calendar months (April-August 2026, i.e. at least 3 of 5); (v) expectancy above the 95th percentile of 200 random-entry runs (seed 20260929; same coins, window, exits, costs and trade count); (vi) concentration <= 0.50 by the formula above.
  **The only number that differs from the forward bar is the trade floor.** The sealed quadrant is a fixed sample of 15 coins x 26 weeks; at the dev-period rate for this rule (about 5.3 trades/week across 15 coins) it holds roughly 140 trades, so a 150 floor would make INCONCLUSIVE likely by construction. 50 is the floor every desk pre-registration used for this quadrant.
- **Outcomes:** all six pass = **CONFIRMED**; fewer than 50 trades = **CONFIRMATION INCONCLUSIVE**; concentration > 0.50 = **CONFIRMATION CONCENTRATED**; any of gates (ii)-(v) fails = **CONFIRMATION FAILED**.

**The ladder — every rung ends in a defined state:**

| Outcome | Next step | End state |
|---|---|---|
| **FAIL** (any of 2-5 fails) | none | **Closed.** No variant (other N, k, s, r, timeframe or coins) is tracked on this or any overlapping window. Sealed quadrant untouched. |
| **INCONCLUSIVE** (< 150 trades by 2027-03-31) | none | **Closed**, as FAIL. No extension, no re-tracking. |
| **PASS-CONCENTRATED** | none | **Closed**, as FAIL. |
| **PASS** | confirmation runs automatically | decided by the confirmation, below |
| PASS → **CONFIRMATION FAILED / INCONCLUSIVE / CONCENTRATED** | none | **Closed.** The desk sealed quadrant is spent. |
| PASS → **CONFIRMED** | the rule becomes a desk card | **A desk card, and nothing more:** shown on the Signals panel, every card graded automatically, **removed after 100 graded cards if realised expectancy after base costs is below 0 R** (then closed). No bot, no automation, no live-account use, no sizing decision — each would need its own separate go/no-go. |

**In every outcome the pause on other research stays in force.** No short-1h result, a CONFIRMED card included, is a reason under §1d (disqualifier 1).

### 3.5 Record of the change to the locked forward document

- `PREREGISTRATION_2026-09-28_short1h_forward.md` is **not edited**; its hash stays `9bb35e11…c0be812`. This note supersedes its **"Decision" section** with §3.4, and narrows its interim-reporting wording (§3.3).
- **Precise claim about the change:** every path that previously led to a desk card now needs more evidence to get there (the concentration check, plus a passing confirmation), and no outcome that was previously a rejection becomes anything else. **The note also adds one action the locked document did not have: a single, automatic use of the desk sealed quadrant as a confirmation sample, which spends that data.**
- **Against revision 1 of this note:** revision 1's post-pass decision point is withdrawn and replaced by the pre-authorised automatic confirmation (§3.4, Trigger). **Against the locked forward document:** the one new action remains the single use of the desk sealed quadrant, which spends it — **authorised in advance, not decided after the result.**
- **Timing:** made 2026-09-29, before any forward trade was graded or could have been (§2).

### 3.6 How the grade is produced

- **Before any grading**, a data-only audit (dates and volumes, no returns) covers the 30 coins across the forward window and the 15 holdout coins across the sealed window. If any coin has a stretch of **>= 24 hours with zero volume or missing bars** in either window, grading stops and the finding is reported to Michael. No handling rule is written after it has been seen; any rule requires a dated amendment approved before grading resumes. **The treatment of affected coins is decided in that amendment; the window is not voided automatically.**
- `research/short1h_forward_grade.py` is written before the checkpoint and **never run on forward data before it**. It imports `desk1h4h_run.py`'s signal and simulation code unchanged, and implements §3.3, the concentration check and the automatic confirmation in §3.4. Its SHA-256, this note's SHA-256 and the forward pre-registration's SHA-256 are recorded before its first run and in its output.
- It runs **once**, at the checkpoint. Forward data (from 2026-09-28) is downloaded for that run only, by `desk_data.py` / `desk_data_1m.py` unchanged or by a new downloader whose hash is recorded before the run.
- The output is reported as run, with the outcome named from the §3.4 ladder, **before** any discussion of what to do next.
