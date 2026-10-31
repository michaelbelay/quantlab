# Families (each registered before it runs)

## F1 funding_ls — crowding (registered 2026-10-04)
Why: a high funding rate means longs are crowded and paying to stay in; crowded sides tend to
unwind, and the short side also *collects* that funding. A low/negative rate is the mirror.
Rule: rank eligible coins by their average funding rate over the lookback; **short the k highest,
long the k lowest**, equal notional.
Grid: k ∈ {3, 5, 8} · lookback ∈ {1, 3, 7} days · rebalance every {8h, 24h} → 18 configs.

## F2 reversal_ls — short-term overreaction (registered 2026-10-04)
Why: big short-term moves in altcoins are often liquidity/flow driven and partly reverse.
Rule: rank eligible coins by return over the lookback; **long the k biggest losers, short the k
biggest winners**, equal notional.
Grid: k ∈ {3, 5, 8} · lookback ∈ {1, 3, 7} days · rebalance every {8h, 24h} → 18 configs.

## Results so far (DEV, 2026-10-04) — see runs/F1_dev.json, runs/F2_dev.json
- **F1 FAIL** (D4): every config profitable (best Sharpe 1.33, survives 2x costs), but drawdown 56–95%.
  Diagnosis (k8, 7d, 24h): funding earned +1,077 USDT; the 58% drawdown (2023-09 → 2024-07) is the
  SHORT leg's price loss (−818): shorts were hot high-beta coins (KAS, JTO, ONDO, WIF), longs calm
  large ones (BCH, BNB, TRX). Equal notional ≠ equal risk.
- **F2 FAIL**: loses in every config; the sign-flipped version (momentum) loses too. No edge. Closed.

## F3 funding_pairs — F1 with volatility-matched pairs (registered 2026-10-04, after F1's diagnosis)
Why: keep F1's funding edge, remove its beta mismatch (wild shorts vs calm longs).
Rule: sort eligible coins by 30-day volatility of 8h returns and cut them into k equal groups;
in each group **long the lowest-funding coin, short the highest-funding coin** (k pairs, equal
notional per position). Same gates as RULES.md; the random twin picks a random long and short
inside each group.
Grid: k ∈ {5, 8, 12} · lookback ∈ {3, 7, 14} days · rebalance every {8h, 24h} → 18 configs.
- **F3 FAIL** (DEV 2026-10-04): volatility-matched pairs did NOT fix it — drawdowns 44–77%, best Sharpe 1.08,
  worse than F1. Beta mismatch was not the whole story. Closed.

## F4 funding_ls_voltarget — F1 + fixed-risk sizing (registered 2026-10-04, before running)
Why: F1's signal is profitable in every config and survives 2x costs; it fails only on drawdown.
Sizing to a constant risk level is the standard cure for that and is not fitted to the data.
Rule: F1 unchanged (same grid). At each rebalance, gross exposure = equity × min(5, 25% / realised
annualised volatility of the strategy's own 8h returns over the last 30 days); 1.0x before 30 days of
history. Both sides stay equal. Each position's leverage = max(1, gross / equity) (isolated margin),
so liquidation distances are those of the leverage actually used. Target 25% is fixed — not tuned.
Gates as RULES.md; the leverage step is replaced by the 5x cap above.
- **F4 FAIL** (DEV 2026-10-04): sizing works (realised vol exactly 25%), Sharpe up to 1.35, 5 of 6 years
  positive — but max drawdown still 55–60%. It is a 10-month bleed, not volatility: 2023-09 → 2024-07
  the short leg lost −994 USDT while crowded coins kept trending up in the alt rally. Closed.

## F5 funding_trendbreak — short crowding only after the trend breaks (registered 2026-10-04, before running)
Why: F1/F4's losses come from shorting high-funding coins that are still trending up; crowding pays
the short side only once the move stalls.
Rule: longs = the k lowest-funding eligible coins (as F1). Shorts = the k highest-funding eligible coins
whose 20-day price change is ≤ 0. Both sides cut to the smaller count so they stay equal. F1 sizing and
leverage step. 20 days fixed, not tuned. Random twin: random coins, same filter on the short side.
Grid: F1's (k ∈ {3, 5, 8} · lookback ∈ {1, 3, 7} d · every {8h, 24h}).
- **F5 FAIL** (DEV 2026-10-04): worse than F1 (best Sharpe 0.92, drawdown 51–88%). Filtering shorts to
  broken trends removed good shorts as well as bad ones. Closed.

## Status 2026-10-04 end of day: 5 families, 0 pass DEV. VALID (280 unseen coins) and FINAL never opened.
What is real: funding crowding (F1) earns money in every setting and survives 2x costs, but suffers a
10-month bleed in the 2023-24 alt rally (shorts on crowded coins that keep rising). Three repairs
(volatility-matched pairs, fixed-risk sizing, trend-break filter) did not remove it.
Trials on DEV so far: 90 configurations (F1 18, F2 18, F3 18, F4 18, F5 18).

## Round 2 (registered 2026-10-05, before running) — three new mechanisms, same gates
All three use a holding band: an existing position is kept while it still ranks inside the best 2k
of its side; empty slots are filled with the best new names. Both sides cut to the smaller count.
Score convention: high = short, low = long.

### F6 carry_momentum — funding crowding blended with medium-term momentum
Why: F1's only failure is crowded coins that keep trending (2023-24); that is precisely when
cross-sectional momentum pays. Blending the two signals is standard multi-factor practice.
Rule: score = pct-rank(7-day mean funding) − pct-rank(L-day price change), ranks across eligible coins.
Grid: k ∈ {5, 8, 12} · momentum L ∈ {14, 30} d · rebalance {24h, 7d} → 12 configs.

### F7 residual_reversal — coin-specific overreaction after removing the market
Why: F2 ranked raw returns, which are mostly market beta. Statistical arbitrage ranks the residual:
the part of a coin's move not explained by the market.
Rule: market = equal-weight mean 8h log return of eligible coins; per coin, beta from the last 30 days;
residual = coin return − beta × market, summed over the last L days. Short the highest residual,
long the lowest.
Grid: k ∈ {5, 8, 12} · L ∈ {1, 3} d · rebalance {8h, 24h} → 12 configs.

### F8 listing_fade — new listings drift down
Why: newly listed perpetuals face token unlocks and fading launch demand.
Rule: shorts = eligible coins whose first bar is ≤ A days ago (newest first); longs = the k eligible
coins with the highest 30-day traded volume among coins listed > 365 days ago.
Grid: k ∈ {3, 5, 8} · A ∈ {60, 180} d · rebalance {24h, 7d} → 12 configs.
- **F6 FAIL at the last DEV step** (2026-10-05): 10/12 configs pass D1–D6 (profit at 2x costs, Sharpe
  1.3–2.0, DD ≤ 35%, beats 100% of 200 random twins). Chosen k12 · 14d · 7d: 300 → 3,095 (CAGR 56%,
  DD 15.2%, Sharpe 2.04, 6/6 years positive), neighbours 100%. Failed the leverage rule even at 1x:
  7 short liquidations over 5 years (coins doubling within a week) = 423 USDT = 13.6% of peak equity
  (limit 10%). The rule stays as written.

## F9 carry_momentum_stop — F6 + protective stop (registered 2026-10-05, before running)
Why: F6's only failure is liquidation of shorts on coins that double inside a week; a real book
stops out before liquidation.
Rule: F6 unchanged (same grid). Each position is closed when price moves 30% against it from entry
(fixed, not tuned); fill at the stop price with an extra 0.5% slippage plus normal costs. A stop or a
liquidation forces a full rebalance at the next bar, so longs and shorts stay equal in count.
Liquidation is checked before the stop (a gap through both = liquidation). Gates as RULES.md.
- **F9 FAIL at VALID** (280 unseen coins, 2026-10-05): 300 → 226, CAGR −5.3%, DD 75.9%, Sharpe 0.15,
  240 stops, 9 liquidations. Dev pass did not transfer. See RULES.md Amendment A1 (survivorship bias in DEV).
- **F9 FAIL FAIR** (Amendment A1, ALL 413 coins, unchanged): CAGR 10.8%, DD 74.4%, loses at 2x costs. Closed.
  Lesson: every DEV result F1–F9 was inflated by the survivor-only DEV coin set.

## Round 3 (registered 2026-10-05, before running) — protocol A1: ALL 413 coins point in time,
## DEV 2021-01-01 → 2024-06-30 · VALID 2024-07-01 → 2026-03-25 · FINAL 2026-03-26 → 2026-09-25
D5 under the time split: at least 3 of the 4 DEV periods (2021, 2022, 2023, 2024H1) positive. All other gates
unchanged. VALID and FINAL keep the earlier history only to feed the signals.
Why this round: on a fair universe most alts bleed or die while large liquid ones survive; these families
target that with information a bot has at the time.

### F10 funding_ls on ALL — F1 unchanged (same grid), re-tested on the fair universe.
### F11 listing_fade on ALL — F8 unchanged (same grid).
### F12 size_ls — liquidity/size factor
Rule: rank eligible coins by average daily traded volume over the lookback; **long the k most traded,
short the k least traded** (still ≥ 10M/24h). Holding band as round 2.
Grid: k ∈ {5, 8, 12} · lookback ∈ {7, 30} d · rebalance {24h, 7d} → 12 configs.
### F13 size_carry — size + funding blend
Rule: score = pct-rank(7-day mean funding) − pct-rank(30-day traded volume); high = short. Holding band.
Grid: k ∈ {5, 8, 12} · funding lookback fixed 7 d · rebalance {24h, 7d} · volume lookback ∈ {7, 30} d → 12 configs.
- **Round 3 DEV (ALL coins, 2021-01 → 2024-06): F10, F11, F12, F13 all FAIL.**
  F10 funding: best Sharpe 1.04 but 2024H1 −39%, DD 60%. F11 listing fade: weak (Sharpe ≤ 0.55).
  F12 size: long most-traded / short least-traded LOSES ~40%/yr 2021-22 — high-attention coins underperformed.
  F13 (funding − volume rank) fails.

## Round 4 (registered 2026-10-05, before running; protocol A1 time split)
F14 is the sign-flip of F12, chosen AFTER seeing F12 — a data-snooping risk stated openly. It can only be
believed if VALID (2024-07 → 2026-03, untouched by every family) passes.
### F14 attention_reversal — short the k most-traded coins, long the k least-traded (eligible, ≥ 10M/24h).
Why: heavy attention/volume precedes weaker returns; small coins carry a premium (Liu, Tsyvinski & Wu 2022).
Grid: k ∈ {5, 8, 12} · volume lookback ∈ {7, 30} d · rebalance {24h, 7d}.
### F15 crowding_attention — score = pct-rank(7-day funding) + pct-rank(volume over lookback); high = short.
Why: combine two independent effects (crowding pays the short side; attention precedes underperformance).
Grid: k ∈ {5, 8, 12} · volume lookback ∈ {7, 30} d · rebalance {24h, 7d}.
- **F14 DEV**: 10/12 configs pass D1–D6 (Sharpe 1.08–1.51, DD 22–34%, profitable at 2x costs). Chosen
  k12 · 30d · 7d: 300 → 913, Sharpe 1.51, DD 25.4%. FAILS the leverage rule at 1x: 7 short liquidations
  (≥ 10% of peak). Same pattern as F6.

## F16 attention_reversal_stop — F14 + the F9 protective stop (registered 2026-10-05, before running)
Rule: F14 unchanged (same grid) + 30% stop from entry, extra 0.5% slippage, forced full rebalance after any
stop/liquidation (identical mechanics to F9, nothing re-tuned). Protocol A1 time split.
- **F15 DEV**: 11/12 configs pass D1–D6 (Sharpe 1.15–2.15, DD 15–33%, profitable at 2x costs). Chosen
  k12 · 7d · 7d: 300 → 1,400, Sharpe 2.15, DD 18.8%. FAILS the leverage rule at 1x: 8 short liquidations.

## F17 crowding_attention_stop — F15 + the F9 protective stop (registered 2026-10-05, before running)
Rule: F15 unchanged (same grid) + identical stop mechanics to F9/F16. Protocol A1 time split.
- **F16 FAIL at DEV** (D7 neighbours 67%; the stop hurts attention reversal). Closed.
- **F17 PASS DEV → FAIL at VALID** (2024-07 → 2026-03, ALL coins): 300 → 130, CAGR −38%, DD 74%;
  2024H2 +36%, 2025 −46%, 2026Q1 −41%. Same pattern as F9: DEV passes break in 2025-26.

## F18 adaptive_selector — walk-forward choice among all registered configs (registered 2026-10-05, before running)
Why: every fixed rule that passed 2021-24 broke in 2025-26. A selector that re-chooses from recent
evidence only adapts to regime change and is out-of-sample by construction.
Candidates: every grid config of F1–F17 (as registered, incl. stops / vol-target), simulated on ALL 413
coins, 2021-01-01 → 2026-03-25, base costs.
Rule: at the start of each calendar quarter (from 2022-01-01), compute each candidate's Sharpe over the
previous 365 days (8h returns); trade the best one for that quarter if its trailing Sharpe ≥ 0.5, else
hold cash. A switch costs 0.2% of equity (close + reopen at 1x). Nothing tuned: 365 d, 0.5, quarterly are fixed.
Gates: VALID gates on 2024-07-01 → 2026-03-25 (profit at base and with 2x switch cost, Sharpe ≥ 0.7,
max DD ≤ 40%); 2022-01 → 2024-06 reported for information. Pass → FINAL (2026-03-26 → 09-25), one look.
Caveat stated up front: the candidate families were designed with knowledge of 2021-24; the selector's
choices are still made from the past only.
- **F18 PASS VALID** (2026-10-05): 2024-07 → 2026-03: 300 → 776, CAGR 73%, Sharpe 1.27, DD 39.1%; 2x switch
  cost 768. Info 2022-01 → 2024-06: CAGR 9.2%, Sharpe 0.44, DD 27.9%. Lumpy: 3 quarters (+51/+40/+49%)
  carry it. Caveats: candidate curves at base costs (2x applies to switches only); VALID period had been
  viewed for F17; candidate families designed this session. FINAL: same rule, nothing changed, quarters
  2026-04-01 and 2026-07-01 picked from the past; Q1 pick carried 2026-03-26 → 03-31.
- **F18 FAIL at FINAL** (2026-03-26 → 09-25, one look): 300 → 195, DD 57.6%. It kept F6|k5|14d|7d
  (trailing Sharpe 2.57) and lost 43.5% in 2026Q2, then +16% in Q3. Closed.

## Status 2026-10-05: 18 families, ~250 configs, 0 survive FINAL. FINAL period now spent.
Every candidate that passed in-sample (F9, F17, F18) broke on the next unseen period.

## Round 5 — positioning (Protocol B, registered 2026-10-05, before running)
Every positioning series is normalised per coin: z = (value − its 30-day mean) / its 30-day std, so coins
with different typical levels are comparable. Score high = short. Grid for each: k ∈ {3, 5} ·
lookback ∈ {1, 3, 7} days (the averaging window of the signal) · rebalance {1 d, 7 d} → 12 configs.
### P1 retail_contrarian — score = z(all-account long/short ratio). Retail unusually long → short.
### P2 smart_vs_retail — score = z(all-account L/S) − z(top-trader position L/S). Retail long while large
traders are not → short; the reverse → long.
### P3 crowded_chase — score = pct-rank(open-interest change) + pct-rank(price change) over the lookback.
New positions piling into a rising coin (late longs) → short; OI falling with price falling → long.
### P4 taker_exhaustion — score = z(taker buy/sell ratio averaged over the lookback). Unusually aggressive
buying → short (exhaustion); aggressive selling → long.
