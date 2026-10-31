# Amendment v3 to PREREGISTRATION_2026-09-28_rotation.md — DRAFT

**Dated 2026-09-29. Status: CANDIDATE — not approved, not applied. No code has been amended and nothing has been run.**
Locked document it amends: `PREREGISTRATION_2026-09-28_rotation.md`, SHA-256 `1bd2aee3759fbbf8057bdbb60f879465d96b223946ebe89fea999a9336a0df6d`. That file is not edited; if approved, this amendment is applied alongside it and both hashes are recorded in every output.

**Evidence base:** data-only audit `research/rotation_audit2.py` → `research/results/rotation_audit2.json`, `rotation_audit2_runs.csv`. It read dates, volumes and archive file listings only. **No returns, no strategy output and no benchmark has been computed on this data by any run.** The only earlier run stopped at the audit stage (see A3).

**Scope:** data handling and audit reporting only. **No strategy rule, parameter, gate, threshold (§9.1), split, cost or hypothesis changes.**

---

## A1. Zero-volume bars are treated as missing bars

**Finding.** Binance's archive keeps publishing hourly bars after a contract stops trading, at a frozen price with volume 0. 144 contracts end in a stretch of such bars that never resumes (100% zero-volume hours), e.g. OCEAN/AGIX from 2024-06-25, FTT from 2022-11-14, MKR from 2025-09-08. As coded, §5's "data stops" never triggers for these: a position held at delisting would exit at the frozen price **without** the §5 3% haircut.

**Rule.** A 1h bar with `volume == 0` is treated as **absent** for every purpose: ranking closes, lookback closes, execution and exit prices, eligibility rules 1-3, gap detection, and delisting detection. §5 then applies **unchanged** to the resulting gaps:
- a no-trading gap that resumes in **less than 7 days**: position held; P&L runs from the last traded price before the gap to the first traded price after it (an exit falling inside the gap waits for the first traded bar);
- see A2 for gaps of 7 days or more.

**Effect on the known cases:** delisted contracts now "stop" at their last traded bar (haircut applies); relaunched tickers (e.g. CVC: frozen 2022-11-29 → trading again 2025-05-16) become new instruments.

## A2. The 7-day boundary is resolved as STOPPED

The locked text says "< 7 days" for a held gap and "longer than 7 days" for a new instrument; exactly 7 days fell in neither. **Resolved:**
- a no-trading gap of **>= 7 days** (7 x 24 hours or more between two traded bars) means the data **stopped**: a held position is closed at the **last traded close with the 3% unfavourable haircut** plus taker cost, in the week the gap began; trading after the gap starts a **new instrument** (history restarts; the 60-day age rule applies again);
- a gap of **< 7 days** is held (A1).

Note, stated so it isn't mistaken for a live-trading rule: the simulator classifies a gap by its eventual length, which is only known afterwards. This matches the locked §5 design (close at the last available close), and its bias is pessimistic for held positions (the haircut is taken even if the price later recovered).

**Edge case, recorded:** one gap cannot be classified because the data ends first: **STGUSDT**, no trading from 2026-09-24 08:00 (1.6 days to the data end). It affects no simulated week (the last sealed-period exit is 2026-09-21 01:00).

## A3. The 90-symbol check is removed; coverage is reported, not gated by an invented number

**Correction of record.** The first run stopped because 85 symbols had January 2021 data against a threshold of **90 that existed only in the code**. It was never part of the locked rules, which say only "most instruments". The stop was reported as rule-required; it was not. **The check is deleted.**

**Coverage, measured on all available evidence** (Binance `onboardDate` for contracts still in `exchangeInfo`; earliest file across five archive datasets — 1h and 1d klines, funding rate, mark price, aggTrades; REST funding history for the 208 delisted symbols):

| | Count |
|---|---|
| Contracts with evidence of existing in January 2021 | **88** |
| of which the 1h klines cover January 2021 | **85 — 96.6%** |
| of those 88, dead by the end of the data | 26 (24 covered) |
| not covered | BNTUSDT (klines start 2023-08-10), BTTUSDT (2021-04-06; evidence 2020-09-14), REEFUSDT (2021-02-22; evidence 2021-01-25) |

**Correction to an earlier statement:** the earlier "69 of 69 still-listed" check used `exchangeInfo`, which also retains delisted/settled contracts (128 of the dead contracts are still in it). It was not a pure survivor set; the 88-contract figure above supersedes it.

**Limit of the bound, unchanged caveat:** a contract with no file in any archive dataset, no `onboardDate` and no REST funding history is invisible to every source used. Such contracts cannot be counted, and the survivorship caveat in §3 stays in full.

**Whether 96.6% (85 of 88 visible) satisfies "most instruments" is Michael's decision and is recorded here when made:** ______

## A4. Corrected audit counts (replace the first audit's figures)

| Item | First audit | Corrected |
|---|---|---|
| Dead contracts (ended before 2026-09-23) | 28 — by **last bar** (wrong: frozen bars count as data) | **156 — by last TRADED bar** (144 end in frozen prints, 12 files simply end) |
| No-trading runs > 24 h | not measured | **255, in 193 symbols** |
| — 1-6 days, resumed | | **98** — archive outages, not suspensions: 97 fall on 2022-02-25 (48) and 2022-03-31 (49), 2-3 days each, 99.3% of the hours are missing bars rather than zero-volume |
| — 1-6 days, never resumed | | **1** — STGUSDT at the data end (A2) |
| — 7+ days, resumed | | **12** — AERGO, AIA, BNX, CTK, CVC, CVX, ICP, LIT, MAVIA, PUMP, SLP, TLM (20 to 899 days) |
| — 7+ days, never resumed | | **144** — delistings; 100% zero-volume hours |
| History cut short at the start | not measured | **7** — BNT (from 2023-08, evidence 2021-01), BTT (2021-04 vs 2020-09), GTC (2021-06 vs 2021-03), MASK (2021-08 vs 2021-07), BZ / CL / NATGAS (2026-04 vs 2026-03) |

**Consequence of the existing locked rule, recorded (not changed):** the two 2022 archive outages are 2-3 day gaps across most instruments at once. Eligibility rule 3 (no gap > 24 h inside the lookback) makes affected coins ineligible for the following 2 weeks (L=14) or 4 weeks (L=28). If fewer than 15 remain eligible, those weeks are cash under the locked MIN_ELIGIBLE rule. This follows from the locked text and is reported, not adjusted.

## A5. Code changes this amendment would authorise (and nothing else)

1. `rotation_run.py`: drop zero-volume bars on load (A1); segment split at gaps **>= 7 days** of no trading (A2); delete the 90-symbol stop (A3); record both documents' SHA-256 in outputs.
2. `rotation_run.py` audit block: dead = last **traded** bar (A4).
3. The report (`ROTATION_REPORT.md`) reproduces A3's coverage table and A4's counts.

Everything else in the locked pre-registration stands as written.

---

## Separate open question — NOT part of this amendment

**Q-U. Non-crypto contracts.** `exchangeInfo` classifies **180** of the 859 contracts as not crypto (`underlyingType` != COIN): 147 US equities and ETFs (incl. leveraged/inverse ETFs such as TQQQ, SOXL, SQQQ, UVXY), 22 HK/KR/CN equities, 8 commodities (gold, silver, platinum, palladium, copper, crude, Brent, natural gas), 2 pre-IPO (OPENAI, ANTHROPIC), 1 crypto index (ALLUSDT). **First bars 2025-08-06 .. 2026-08-28; 160 of 180 first appear in 2026 Q2-Q3**, so after the 60-day age rule they enter eligibility almost entirely inside the **sealed period**, and could take top-40 volume slots in the one check meant to be clean.

The locked §3 includes them by its letter ("every USDT-margined perpetual ... nothing else is excluded by name"); §1 frames the question as ranking **coins**. The 29 symbols no longer in `exchangeInfo` cannot be typed, but 28 of them first traded before 2025, before these products existed.

This needs its own decision before any run.
