# Pre-registration: regime-switching book, 2026-10-07

Status: **approved by Michael 2026-10-07 ("go ahead").** No strategy result had been split by market type when this
was written. This text and `research/regime_switch.py` are hashed (sha256) into `research/regime_switch/hashes.txt`
before the first run; the fit choice is hashed before any test-window trade is read.

## Why this test
Our gate G3 required a strategy to be positive in ≥ 3 of 4 market periods (bull 2021, bear 2022, recovery 2023-24,
recent 2025-26). That rejects specialists by design. Example: `rel_strength(n=168, thr=0.03) · volume · long` made
+7751 in bull 2021 and +7833 in recovery 2023-24, lost −1407 in bear 2022 and −71 in 2025-26, and was rejected for
that reason only (CAMPAIGN_2026-10-04.md).

Michael's point (2026-10-07): no strategy wins in every market; the system should switch strategies by market type.
This test asks the question that matters: **can a switch that only knows the past pick the right specialists in
time, and earn after costs?** The switching book is tested as one strategy.

Known evidence against (stated now, before the run): the BTC trend filter made all 8 rotation variants worse
(PAUSE_NOTE_2026-09-29.md §1); the C40 trend gate did not rescue the funding family (FAMILIES_C.md); market types
last ~10 days on average (measured on BTC only, see below), so a late switch costs a real share of each one.

## 1. Market type (computed from BTC only, known at the previous daily close)
From `BTC_USDT_USDT-1d-futures.feather`, daily closes:
- **Trend**: close > 50-day simple average → `UP`, else `DN`.
- **Volatility**: 20-day standard deviation of daily log returns, compared with its own rolling 365-day median
  (needs at least 60 days of history) → `HIVOL` above, `LOVOL` at or below.
- Four types: `UP_LOVOL`, `UP_HIVOL`, `DN_LOVOL`, `DN_HIVOL`. The type for day D uses data up to the close of D−1
  (shifted one day: no look-ahead). Days without enough history have no type and are never traded.
- A trade gets the type of its **entry** day. The switch does not close open trades when the type changes (the
  strategy's own exit rules apply), which matches how it would run live.

Days per type (BTC only; counted 2026-10-07 to check the sample is big enough; first typed day 2021-03-22):
| Window | UP_LOVOL | UP_HIVOL | DN_LOVOL | DN_HIVOL | no type |
|---|---|---|---|---|---|
| Fit 2021-01-01 .. 2023-12-31 | 333 | 136 | 343 | 203 | 80 |
| Test 2024-01-01 .. 2026-09-18 | 360 | 192 | 164 | 276 | 0 |

Average run of one type: 9.5 days.

## 2. Pool of strategies (fixed, nothing new is designed)
All **284 pipeline candidates** that have a development trade file (`research/pipeline/trades/<id>__dev.parquet`,
133 development coins, 1h, after base costs 0.1% per side incl. slippage, notional 100 per trade). Rejected ones
included: that is the point. No rule, parameter or exit is changed.

## 3. Fit: assign specialists to market types (entries 2021-01-01 .. 2023-12-31 only)
For each (candidate, market type) cell, using only fit-window trades:
1. at least **100 trades** in that type;
2. **PF ≥ 1.15** after base costs, and **PF ≥ 1.05** after an extra 0.2 per trade (= 2× costs);
3. **day-weighted t ≥ 3.0** (trades of one entry day averaged first, same rule as the scanner; t = mean / sd ×
   √days over days with a trade). 284 × 4 = 1136
   cells, so ~1.5 cells would pass t ≥ 3 by luck alone; this is why the test window decides, not the fit;
4. positive in **both** fit halves (2021-22 and 2023); a half with fewer than 20 trades in that cell is ignored.

Per type keep the **top 3 by t** that pass, skipping a candidate whose fit trades overlap > 70% (coin, entry day,
side) with one already kept. A type with no passing cell is **cash** (no trades in that type). If fewer than 2 of the
4 types get a strategy, the test stops: **no switching book can be built** and that is the result.

The chosen list (candidate ids per type) is written to `regime_switch_choice.json` and frozen (hashed) **before**
any test-window trade is read.

## 4. Test A: same 133 development coins, entries 2024-01-01 .. 2026-09-18
Switching book = the chosen candidates' trades, taken only when the entry-day type matches their assigned type.
Each type's strategies get equal weight (trade P&L ÷ number of strategies in that type). Book P&L per day = sum of
weighted trade P&L by entry day; PF on weighted trade P&L; "day-weighted t" for the book = mean / sd × √n of the
daily book P&L over days with a trade.

Pass needs **all** of:
- A1. PF ≥ 1.10 after base costs, and PF ≥ 1.00 after the extra 0.2 per trade;
- A2. day-weighted t ≥ 2.0;
- A3. positive in ≥ 2 of 3 test periods (2024, 2025, 2026-01..09);
- A4. **the switch adds value**: higher average P&L per calendar day of the test window than the same chosen
  candidates traded in every type (no switch, each distinct candidate weighted 1 ÷ number of distinct candidates);
- A5. **better than a random switch**: 1000 runs where the type labels of the test window are shuffled in blocks of
  30 days (keeps the persistence of real types; seed 20261007); the real book's total must be ≥ the 95th percentile.

Contamination stated: the candidates were judged by the pipeline on all development years including 2024-26, so test
A is not clean, only the type assignment is out-of-time. That is why test B exists.

## 5. Test B: 280 unseen coins (on purpose use, pre-registered here), same test window
Only if test A passes. The chosen candidates are run on the 280 unseen coins (`oos_universe.json`) with the pipeline
engine (`research/pipeline/run.py` `run_pass`, unchanged), entries 2024-01-01 .. 2026-09-18, same switching rule.
Same checks A1-A5. Any chosen candidate that is one of the 11 that already ran on the unseen coins is flagged in the
report (that data was seen once for it).

## 6. Decision
| Result | Class | Next step |
|---|---|---|
| Fewer than 2 types filled at fit | 🔴 | Recorded: our pool has no specialists a switch can use |
| Test A fails any of A1-A5 | 🔴 | Recorded with the failing checks; A4/A5 fail = the switch itself adds nothing |
| A passes, B fails | 🟠 | Recorded; no forward test |
| A and B pass | 🟡 | 300 USDT portfolio simulation (`research/cap300/sim.py`, DD ≤ 40%), then a paper forward test. 🟢 never before the forward test |

No re-run with other thresholds, other type definitions (e.g. 100-day average, funding-based types), or another
fit window after the result is seen. A different definition is a new pre-registration and counts as a new trial.

## 7. Data rules
Development coins and the BTC daily file only, plus the 280 unseen coins in test B as stated. The sealed desk
quadrant (`desk_data`) is not read. Out-of-time 2017-20 data is not used.
