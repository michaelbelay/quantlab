# Bear lab discovery log

## 2026-11-02 (first run; 6 ideas, 6 screens, 1 passed, 1 added)
Theme: deep bear (BTC under a falling 200-day average) is the only regime where these coins fell, so 5 of 6 ideas
need DEEP. One idea is about token supply (unlocks) as a reason that still holds in 2024–26.

| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day t | result |
|---|---|---|---|---|---|---|---|
| deep_ema_reject | trapped holders sell at break-even when a deep-bear bounce reaches the falling 480h EMA | 173 (64/109) | -0.20% | +0.73% | +0.18% | 0.98 | failed (half A < 0) |
| deep_levered_bounce | longs adding leverage (OI +8%/72h) into a deep-bear bounce get flushed | 365 (152/213) | -0.87% | +1.53% | +0.33% | 1.01 | failed (half A < 0) |
| deep_funding_carry | longs still paying funding >= +0.01% under a falling EMA in a deep bear are bag-holders; short collects carry | 555 (314/241) | +0.80% | +0.39% | +0.42% | 1.43 | **passed, added** (paper from 2026-11-02 04:00 UTC) |
| unlock_coin_rally_fade | unlock/emission sellers (ARB, SUI, WLD, ENA, PUMP, TAO) use 72h +10% rallies as exit liquidity | 165 (18/147) | -0.64% | +0.75% | +0.40% | 0.84 | failed (only 18 trades in half A) |
| deep_quiet_grind | quiet weeks in a deep bear precede a flush | 236 (85/151) | -1.25% | -0.18% | -0.76% | -1.09 | failed (loses in both halves) |
| deep_alt_outrun_btc | a lone alt pump (+8 pts vs BTC in 72h) in a deep bear has no market bid | 227 (103/124) | -1.25% | +0.74% | -0.37% | 0.09 | failed |

Notes: SOL 2023-01-01/02 (bounce out of the FTX low) is the worst trade in 3 ideas – deep-bear bounce shorts got
caught at the turn of the cycle. deep_funding_carry is close to the old U family (funding >= 0.01% under EMA480) but
adds the deep-bear filter and a falling EMA; its day t is only 1.43, so the forward verdict will decide. Failed ideas
were not re-tuned (6 screens unused).


## 2026-11-02 (main session, OI round 3; 6 ideas, 6 screens, 0 passed)
Theme: positioning data (top traders, retail accounts, taker flow, OI growth). Written and screened once, not re-tuned.

| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day t | result |
|---|---|---|---|---|---|---|---|
| oi_top_crowd_long | top traders at their most long-heavy in a downtrend are the next forced sellers | 562 (117/445) | +1.06% | -0.56% | -0.42% | -1.16 | failed (half B < 0) |
| oi_taker_sell_new_oi | aggressive selling plus new OI = funded shorts that keep pushing | 490 (166/324) | +0.08% | -0.51% | -0.51% | 0.06 | failed (half B < 0) |
| oi_retail_long_whale_short | crowd long, big books short: the big books know more | 785 (227/558) | -0.02% | -0.74% | -0.73% | -1.95 | failed (both halves < 0) |
| oi_absorbed_buying | market buys absorbed without a price rise = a seller distributing | 1535 (481/1054) | +0.13% | -0.19% | -0.29% | -0.91 | failed (half B < 0) |
| deep_carry_oi_build | deep bear, longs paying carry and adding OI 10%/7d | 110 (74/36) | +0.10% | -0.50% | -0.30% | 0.07 | failed (half B < 0) |
| oi_flat_price_lev_up | OI +20% in 7d with price flat in a downtrend resolves down | 105 (57/48) | +0.11% | -0.08% | -0.18% | 0.02 | failed (half B < 0) |

Notes: same pattern as every earlier batch – positive in 2022-24, negative from 2024-05. Positioning extremes in the
2024-26 market get squeezed (ENA and ZEC are the repeat worst trades). Adding OI growth to deep_funding_carry made it
worse (+0.39% → -0.50% in half B), so the carry edge does not come from leverage build-up.


## 2026-11-02 (daily agent, run 2; 6 ideas, 6 screens, 1 passed, 1 added)
Theme: who is left after a move – covered shorts, thin bounces, outliers, squeezes, holdout longs – plus a relative
(cross-coin) version of the carry idea. Screen count after this run: 18.

| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day t | result |
|---|---|---|---|---|---|---|---|
| squeeze_done_short | funding back >= 0 after <= -0.01% in 72h: shorts covered, no squeeze fuel left | 1105 (439/666) | -0.63% | -0.48% | -0.74% | -2.91 | failed (both halves < 0) |
| funding_top3_deep | deep bear: coin in the top 3 funding of the 19 (> 0, under EMA480) is the most crowded long book | 758 (357/401) | +0.28% | +0.50% | +0.19% | 0.82 | **passed, added** (paper from 2026-11-02 17:00 UTC) |
| thin_volume_bounce | +6%/72h bounce under a falling EMA on < 80% of prior volume = covering, no new buyers | 459 (145/314) | -2.23% | -0.71% | -1.39% | -1.99 | failed (both halves < 0) |
| outlier_break_deep | deep bear: alt +15 pts vs BTC over 30d loses its 168h EMA and catches down | 72 (33/39) | -0.01% | -0.51% | -0.48% | -0.67 | failed (< 100 trades, both halves < 0) |
| failed_squeeze | squeeze (1h +3%, OI -2%) fully round-tripped in 48h: shorts gone, no buyers | 20 (11/9) | -2.82% | -6.01% | -4.45% | -2.96 | failed (20 trades, loses) |
| carry_while_deleveraging | OI -10%/7d but funding >= +0.01% under a falling EMA: longs are the holdouts | 584 (287/297) | -0.08% | -0.60% | -0.54% | -0.14 | failed (both halves < 0) |

Notes: funding_top3_deep is a cousin of deep_funding_carry (same regime, funding as the signal) and its day t is only
0.82, so the two paper results will be correlated; count them as one bet when reading the forward results. Outside a
deep bear every funding/flow idea lost again in half B. Shorts entered on 2025-10-10/11 (the October liquidation wick and
rebound; ENA twice, XRP once) are among the worst trades in 3 ideas. thin_volume_bounce lost most (-2.2% in half A): low-volume bounces kept going. Failed
ideas were not re-tuned (6 screens unused). 2 of today's 3 entry slots are used.

## 2026-11-02 (main session, round 4: timing and flow; 6 ideas, 6 screens, 0 passed)
| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day t | result |
|---|---|---|---|---|---|---|---|
| btc_lead_catchdown | alt that held up during a -1.5% BTC hour catches down within 6h | 377 (183/194) | -0.69% | -0.68% | -0.88% | -1.85 | failed |
| weekend_pump_fade | weekend +4% rallies on thin books fade on Monday | 140 (55/85) | -1.84% | +1.55% | +0.02% | 0.32 | failed (half A < 0) |
| us_open_short | weak coins sold in US hours during bears (13:00 UTC, 8h) | 5588 (2211/3377) | -0.37% | -0.06% | -0.38% | -1.60 | failed |
| prefunding_long_exit | longs close before a high funding bill (>= 0.03%) | 192 (178/14) | -0.08% | -0.88% | -0.34% | -0.47 | failed |
| blowoff_wick | top-1% volume bar with an upper wick after +5%/24h | 27 (13/14) | -2.21% | +2.08% | -0.19% | -0.29 | failed (27 trades) |
| weekly_high_reject | rejection >= 3% at the prior 168h high in a downtrend | 25 (11/14) | -3.88% | -0.55% | -2.21% | -1.95 | failed |

## 2026-11-02 (main session, round 5: the coin's own deep bear; 6 ideas, 6 screens, 1 passed, 1 added)
Idea: replace BTC's deep-bear filter by the coin's own (close under its falling 200-day average), so the carry idea
can trade in a shallow BTC bear like today's.

| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day t | result |
|---|---|---|---|---|---|---|---|
| **cdeep_funding** | longs paying funding >= 0.01% on a coin in its own deep bear bleed out | 666 (254/412) | +0.72% | +0.19% | +0.19% | 1.20 | **passed, added** (paper from 2026-11-02 18:00 UTC) |
| cdeep_top3_funding | top-3 funding among coins in their own bear | 836 (245/591) | -0.08% | -0.23% | -0.39% | -0.49 | failed |
| cdeep_breakdown_oi | new 30-day low on rising OI | 73 (36/37) | +0.85% | -0.14% | +0.15% | 0.45 | failed |
| cdeep_rally_fade | +8%/72h rally in the coin's own bear | 253 (48/205) | -1.70% | +0.47% | -0.15% | 0.24 | failed (half A < 0) |
| cdeep_rel_weak | coin losing >= 5 pts to BTC in 7d | 367 (96/271) | -0.45% | -1.38% | -1.34% | -2.68 | failed |
| cdeep_funding_flip | funding flips positive after <= 0 | 413 (134/279) | -0.39% | +0.02% | -0.31% | -0.70 | failed |

Notes (diagnostics after the add, nothing changed): cdeep_funding by year +0.71% / +0.79% / -1.16% / +0.09% / +1.16%
(2022..2026); trades when BTC itself was not in a deep bear: 347 at +0.21%, in a BTC deep bear: 319 at +0.58%. It fired
on XRP, DOGE and ADA in the last 72h, so unlike the other two it can trade in today's shallow bear. 3 of today's 3 entry
slots are used; screens after this need tomorrow's slots.

## 2026-11-02 (main session, round 6: positioning inside the coin's own deep bear; 6 ideas, 6 screens, 1 passed, 0 added)
| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day t | result |
|---|---|---|---|---|---|---|---|
| cdeep_retail_long | retail long-heavy in a coin's own bear | 569 (224/345) | +0.37% | -0.25% | -0.20% | -0.18 | failed |
| cdeep_oi_peak | OI at a 30-day high in a coin's own bear | 90 (36/54) | +0.18% | -0.22% | -0.26% | -0.08 | failed |
| cdeep_absorbed_buying | taker buying absorbed in a coin's own bear | 768 (219/549) | -0.21% | -0.35% | -0.51% | -1.08 | failed |
| cdeep_ema_reject | bounce rejected at the 480h EMA | 51 (15/36) | -0.54% | +1.00% | +0.34% | 0.31 | failed (51 trades) |
| **cdeep_funding_persist** | longs paying funding for 9 settlements in a row in a coin's own bear capitulate together | 368 (147/221) | +1.23% | +0.61% | +0.66% | 2.53 | **passed, NOT added (0 slots left today) – add on 2026-11-03** |
| cdeep_vol_squeeze | volatility compression in a coin's own bear | 446 (141/305) | +0.81% | -1.52% | -0.98% | -1.98 | failed |

Diagnostics for cdeep_funding_persist (report only): by year +1.08% / +1.56% / -1.01% / +0.60% / +1.67% (4 of 5 years
up); BTC not in deep bear 199 trades +0.75%, BTC deep 169 trades +0.98%; 26/43 months positive; top-3 months = 76% of
profit (fails A2's 50% gate); average without the 10 best trades +0.41%; 54 stop-outs at -8.2%; closed-trade equity on
300 USDT (50 per trade) 300 → 457, max drawdown 13.9%. Caveat: it is a subset of cdeep_funding found in the same
session, so its history numbers are partly selected; only the paper result counts. Fired on XRP and DOGE in the last 72h.
