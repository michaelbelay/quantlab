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

## 2026-11-03 (daily agent; 6 ideas, 6 screens, 0 passed, 0 added)
cdeep_funding_persist was already on paper (since 2026-11-03 08:00 UTC; the add attempt said "exists"), so 1 of
today's 3 slots was used before this run. Theme: test the carry edge from different sides (stronger premium, entry on a
bounce, trend alignment, longer hold, relative weakness) plus one supply idea (first-year tokens). Screens: 37–42.

| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day t | result |
|---|---|---|---|---|---|---|---|
| cdeep_funding_hot | funding >= 0.015% (above the 0.01% floor) = real perp premium in a coin's own bear | 1 (0/1) | – | -2.27% | -2.47% | 0.00 | failed (1 trade) |
| young_supply_short | first-year tokens under a falling EMA: unlock/airdrop supply with no bid | 282 (98/184) | -0.69% | -1.56% | -1.45% | -3.04 | failed (both halves < 0) |
| cdeep_funding_bounce | carry payers sell their first +3%/24h bounce | 221 (52/169) | -0.72% | -0.42% | -0.69% | -0.13 | failed (both halves < 0) |
| cdeep_funding_stacked | carry payers with close < EMA168 < EMA480 are losing now | 499 (196/303) | +0.62% | -0.12% | -0.03% | -0.45 | failed (half B < 0) |
| cdeep_carry_week | carry short held 168h, 12% stop: slow bleeding needs time | 426 (157/269) | +0.26% | +0.13% | -0.02% | 0.33 | failed (2x costs < 0) |
| cdeep_funding_laggard | carry payers on a coin 10+ pts behind BTC over 30d | 309 (98/211) | -0.06% | -0.09% | -0.28% | -0.35 | failed (both halves < 0) |

Notes: in a coin's own deep bear the funding almost never settles above 0.015% (1 trade in 4.7 years), so the "carry"
edge in cdeep_funding is the default 0.01% rate, i.e. the absence of short crowding, not a long premium. Every filter
added to cdeep_funding (bounce, trend stack, laggard) made half B worse; the plain version stays the best of the family.
Young tokens lost hardest (QNT 2022, ENA 2025 among the worst): first-year coins get squeezed, they do not bleed.
Failed ideas were not re-tuned (6 screens unused). 2 entry slots left today, unused.

## 2026-11-04 (daily agent; 8 ideas, 8 screens, 1 passed, 1 added)
Theme: the coin's own deep bear from new angles (trend alone, broken coins, dip buyers re-levering, failed bounces, no bid
on BTC rallies, market-wide leverage, calm vs wild bear). Screens: 43–50.

| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day t | result |
|---|---|---|---|---|---|---|---|
| cdeep_trend_daily | own deep bear + falling EMA480 alone, once a day (no funding) | 1182 (344/838) | -0.25% | -0.39% | -0.55% | -1.17 | failed (both halves < 0) |
| cdeep_market_lev | coin pays >= 0.01% while the average funding of the 19 is >= 0.01% | 3 (2/1) | +4.04% | +4.28% | +3.92% | 7.02 | failed (3 trades) |
| cdeep_broken_coin | coin >= 50% under its 200-day high: only underwater holders | 864 (169/695) | -0.07% | -0.49% | -0.61% | -1.72 | failed (both halves < 0) |
| cdeep_dip_relever | -10%/72h yet funding still >= 0.01%: leveraged dip buyers | 79 (26/53) | +3.97% | -0.92% | +0.49% | 0.13 | failed (< 100 trades, half B < 0) |
| cdeep_bounce_failed | +12% bounce off the 30d low, then back under EMA168: trapped bounce buyers | 388 (66/322) | -0.44% | -0.17% | -0.42% | -1.38 | failed (both halves < 0) |
| cdeep_no_bid_btc_up | BTC +3%/24h, coin < +1%: holders sell every market bid | 127 (36/91) | +0.32% | -0.60% | -0.54% | -0.33 | failed (half B < 0) |
| cdeep_market_lev_v2 | same as cdeep_market_lev with the average over each coin's last settled funding | 3 (2/1) | +4.04% | +4.28% | +3.92% | 7.02 | failed (3 trades) |
| **cdeep_funding_calm** | cdeep_funding only when BTC 20d volatility <= its 1-year median: slow bleed, no squeezes | 361 (186/175) | +0.88% | +0.39% | +0.44% | 2.13 | **passed, added** (paper from 2026-11-04 08:00 UTC) |

Notes: the coin's own downtrend alone loses (-0.35% over 1182 trades), so in cdeep_funding the edge comes from the funding
condition, not the trend. Broken coins and failed bounces lose in 2024-26 too: underwater coins get squeezed.
cdeep_market_lev_v2 was meant to fix what I thought was a bug (the average used only coins settling that hour). It gave the
same 3 trades, so that was not the cause: the 19-coin average funding is almost never >= 0.01% while a coin is in its own
deep bear. That makes it a wasted screen.
cdeep_funding_calm is a subset of cdeep_funding (on paper since 2026-11-02), so their paper results will be correlated;
count them as one bet. Its worst trades are SOL/ADA in early 2023 (bounce out of the cycle low). 4 screens and 2 entry slots unused.

## 2026-11-05 (daily agent; 6 ideas, 6 screens, 3 passed, 3 added)
Theme: the carry edge in cdeep_funding seems to come from the short side not being crowded. Each idea tests one
explanation of why shorts get squeezed in 2024-26 (thin float, coin volatility, a recent squeeze, OI build or flush, how
far the coin has fallen). Screens: 51–56.

| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day t | result |
|---|---|---|---|---|---|---|---|
| cdeep_funding_oi_drain | price and OI both down 72h (-5% OI) with funding >= 0.01%: longs selling out, no new shorts | 217 (97/120) | +0.69% | -0.33% | -0.07% | 0.15 | failed (half B < 0) |
| **cdeep_funding_majors** | cdeep_funding on the 8 large caps only: wide holder base sells slowly, thin alts squeeze | 282 (123/159) | +0.76% | +0.59% | +0.47% | 2.04 | **passed, added** (paper from 2026-11-05 08:00 UTC) |
| **cdeep_funding_coin_calm** | cdeep_funding while the coin's own 20d volatility <= its 1-year median | 499 (207/292) | +0.80% | +0.55% | +0.46% | 2.01 | **passed, added** (paper from 2026-11-05 08:00 UTC) |
| cdeep_early_bear | cdeep_funding while the coin is <= 35% under its 200-day high (holders not yet capitulated) | 85 (50/35) | +1.98% | +0.78% | +1.28% | 2.04 | failed (85 trades < 100) |
| **cdeep_funding_no_squeeze** | cdeep_funding with no +15% 72h rally in the last 14 days | 528 (210/318) | +0.64% | +0.35% | +0.26% | 1.19 | **passed, added** (paper from 2026-11-05 08:00 UTC) |
| cdeep_funding_oi_low | cdeep_funding while OI is in the lowest quarter of its last 30 days | 346 (146/200) | -0.12% | +0.53% | +0.05% | 0.42 | failed (half A < 0) |

Notes: all three ideas that passed are subsets of cdeep_funding (on paper since 2026-11-02), so they overlap with it and
with cdeep_funding_calm / cdeep_funding_persist. Read the whole family as one bet, not five. Of the subsets, majors and
coin_calm give the best half B (+0.59% / +0.55% vs +0.19% for the plain version), which fits the idea that squeezes in
thin, volatile alts are what break shorts. SOL 2023-02-09 is the worst trade in 5 of the 6 ideas (the bounce out of the
cycle low again). cdeep_early_bear looked strong but had too few trades; it was not re-tuned. 6 screens unused; all 3
entry slots used.

## 2026-11-06 (daily agent; 6 ideas, 6 screens, 3 passed, 3 added)
Theme: what the market around the coin is doing when the carry signal fires (BTC breaking down, sector breadth, BTC's
weekly trend, the coin's own day), plus two ideas without funding (re-levering after a crash, dying volume). Screens: 57–62.

| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day t | result |
|---|---|---|---|---|---|---|---|
| btc_breakdown_carry | BTC new 30-day low in the last 24h sets off liquidations; carry payers in their own bear get flushed | 127 (51/76) | -1.32% | +3.17% | +1.17% | 1.25 | failed (half A < 0) |
| **cdeep_funding_breadth** | >= 60% of coins in their own deep bear: money leaving the sector, no rotation bid | 390 (153/237) | +0.78% | +0.53% | +0.43% | 2.22 | **passed, added** (paper from 2026-11-06 08:00 UTC) |
| **cdeep_funding_weak_day** | carry payers on a red day (24h < 0, close in lower half of 24h range) keep selling | 386 (168/218) | +1.07% | +0.45% | +0.52% | 0.94 | **passed, added** (paper from 2026-11-06 08:00 UTC) |
| **cdeep_funding_btc_weak** | BTC under its 168h EMA: no BTC-led rally to squeeze alt shorts | 523 (212/311) | +0.82% | +0.07% | +0.17% | 0.69 | **passed, added** (paper from 2026-11-06 08:00 UTC) |
| post_crash_relever | after a BTC -10%/7d crash, coins whose OI is fully back while price is still -10% are re-levered dip buyers | 705 (273/432) | -0.12% | -0.64% | -0.64% | -1.33 | failed (both halves < 0) |
| cdeep_volume_dying | 7-day volume in its lowest 10% of 180 days in a coin's own bear: no bid for steady sellers | 747 (186/561) | +0.17% | -0.33% | -0.40% | -0.10 | failed (half B < 0) |

Notes: all three ideas that passed are subsets of cdeep_funding (on paper since 2026-11-02), so they overlap with the five
family members already on paper. Count the whole family (now 8) as one bet. cdeep_funding_btc_weak is the weakest pass
(half B +0.07%, below the plain cdeep_funding's +0.19%, day t 0.69); it was entered because it passed, but it adds little.
breadth is the only one with day t > 2. btc_breakdown_carry had a strong half B (+3.17%) but lost in half A and has few
trades; not re-tuned. Both non-funding ideas lost in 2024-26 again (ZEC and ENA squeezes are the worst trades in
post_crash_relever). SOL 2023-02-09 is again the worst trade in two ideas. 6 screens unused; all 3 entry slots used.

## 2026-11-07 (daily agent; 6 ideas, 6 screens, 2 passed, 2 added)
Theme: the cdeep_funding family already has 8 members on paper, so 4 of 6 ideas test other mechanisms: alts bleeding
against BTC, stops under the 30-day low, retail averaging down, news pumps used as exit liquidity. One family idea
changes only the exit (5% take-profit). Screens: 63–68.

| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day t | result |
|---|---|---|---|---|---|---|---|
| alt_btc_bleed | alt/BTC ratio under its falling 200-day average (no funding): 2024-26 new money bids only BTC | 1249 (327/922) | +0.06% | -0.38% | -0.46% | -0.78 | failed (half B < 0) |
| **cdeep_low_break_carry** | coin in its own bear closes under its 30-day low while longs still pay funding: their stops sit under the obvious low | 111 (49/62) | +1.57% | +1.52% | +1.34% | 0.54 | **passed, added** (paper from 2026-11-07 08:00 UTC) |
| **cdeep_funding_take** | cdeep_funding with a 5% take-profit: 2024-26 dip buyers reverse flushes within days, so bank them | 689 (262/427) | +0.46% | +0.47% | +0.26% | 2.47 | **passed, added** (paper from 2026-11-07 08:00 UTC) |
| retail_averaging_down | own deep bear, price -5%/7d while the retail long/short ratio rises 10%: new trapped longs | 619 (241/378) | +0.65% | -0.00% | +0.05% | 0.13 | failed (half B < 0) |
| bear_news_pump | own deep bear, 1h +4% on 5x volume: underwater holders sell the news spike | 113 (30/83) | -0.39% | -1.24% | -1.21% | -2.36 | failed (loses in both halves) |
| alt_btc_bleed_carry | carry signal with the bear measured against BTC instead of in USD | 896 (335/561) | +0.31% | +0.10% | -0.03% | -0.02 | failed (2x costs < 0) |

Notes: cdeep_low_break_carry has the highest per-trade average so far in both halves (+1.5%), but day t is only 0.54
(day average +0.49%): wins cluster on a few crash days and there are only 111 trades, so it may take long to reach 40
forward trades. It is the first pass whose trigger is a price event (a breakdown), not the funding bar, though it still
needs funding >= 0.01%. cdeep_funding_take is a family member (same entries as cdeep_funding); the take-profit lifted
half B from +0.19% to +0.47%, day t 2.47. Count it with the other 8 as one bet.
Ideas without the funding condition lost again in 2024-26 (alt_btc_bleed, news pumps). bear_news_pump's worst trade is
SOL 2022-11-09 at -26% despite a 10% stop – most likely the very negative funding shorts paid in the FTX crash (not
checked). SOL 2023-02-09 is again the worst or near-worst trade in 3 ideas. Failed ideas were not re-tuned; 6 screens
and 1 entry slot unused.

## 2026-11-08 (daily agent; 6 ideas, 6 screens, 2 passed, 2 added)
Theme: who is trapped inside a coin's own deep bear – stops under a recent low, failed 200-day reclaims, big accounts
leaving, stale leverage, longs in denial – plus the timing of the BTC bear spell. Screens: 69–74.

| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day t | result |
|---|---|---|---|---|---|---|---|
| **cdeep_low_break_14d** | carry payers' stops sit under the 2-week low; the break fires them | 146 (67/79) | +0.86% | +0.56% | +0.49% | -0.12 | **passed, added** (paper from 2026-11-08 08:00 UTC) |
| cdeep_failed_reclaim_200 | leveraged buyers of a failed reclaim of the falling 200-day average are trapped | 174 (73/101) | +0.76% | -1.07% | -0.51% | -0.39 | failed (half B < 0) |
| cdeep_top_derisk | top traders cut longs >= 10%/72h while the rest still pay funding | 230 (44/186) | -0.31% | -0.21% | -0.43% | -0.52 | failed (both halves < 0) |
| cdeep_oi_heavy_carry | OI / 24h volume in its top 10% (stale leverage) while longs pay funding | 242 (99/143) | +0.62% | -0.56% | -0.27% | 0.43 | failed (half B < 0) |
| **cdeep_young_bear_spell** | cdeep_funding only in the first ~3 days of a BTC bear spell: longs still set up for the last up-move must de-lever | 136 (58/78) | +4.14% | +0.48% | +1.84% | 2.95 | **passed, added** (paper from 2026-11-08 08:00 UTC) |
| cdeep_denial_carry | longs still paying funding after a -20% month are in denial | 249 (68/181) | -0.54% | -0.24% | -0.52% | -1.58 | failed (both halves < 0) |

Notes: cdeep_young_bear_spell has the best day t so far (2.95), but half A (+4.1%) carries most of it and half B is only
+0.48%; it is a cdeep_funding subset, so count it with that family (now 11). Its worst trade is SOL 2023-02-09 again.
cdeep_low_break_14d passed on per-trade numbers, but its day-weighted average is negative (-0.09%, day t -0.12): a few
big crash days carry it, and the verdict uses the day average, so it will likely be killed. It overlaps with
cdeep_low_break_carry (30-day low); count them as one bet. Positioning data (top traders, OI/volume) lost again in
2024-26, and so did deeply fallen coins (denial). NEAR 2025-10-18 is the worst trade in 3 ideas (the October rebound).
Failed ideas were not re-tuned; 6 screens and 1 entry slot unused.

## 2026-11-09 (daily agent; 6 ideas, 6 screens, 4 passed, 3 added)
Theme: the carry family is the only one that holds up in 2024-26, so this run combines its two best half-B changes
(large caps, calm coin, take-profit), tests a shorter hold, and adds three context filters (BTC funding soft, thin
turnover, lower weekly high). Screens: 75–80.

| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day t | result |
|---|---|---|---|---|---|---|---|
| **cdeep_funding_majors_take** | large caps sell slowly, but 2024-26 dip buyers reverse flushes: take 5% | 287 (125/162) | +0.46% | +0.39% | +0.22% | 2.03 | **passed, added** (paper from 2026-11-09 08:00 UTC) |
| cdeep_funding_quick | carry payers' selling is front-loaded; hold 24h only | 705 (271/434) | +0.11% | +0.15% | -0.07% | 1.20 | failed (2x costs < 0) |
| cdeep_alt_payer_btc_hedged | alt longs still pay full funding while BTC funding is under default: stale alt book | 580 (219/361) | +0.39% | -0.04% | -0.08% | -0.19 | failed (half B < 0) |
| cdeep_funding_thin_bid | carry payers with 24h turnover under its 30d median: no new buyers | 512 (204/308) | +0.50% | +0.02% | +0.01% | 0.38 | passed, NOT added (weakest pass, 3 slots used) |
| **cdeep_funding_majors_calm** | calm large cap in its own bear with longs paying funding just bleeds | 228 (104/124) | +0.75% | +1.00% | +0.69% | 2.29 | **passed, added** (paper from 2026-11-09 08:00 UTC) |
| **cdeep_funding_lower_high** | lower weekly high: bounce buyers sold into, payers are next | 560 (213/347) | +0.30% | +0.20% | +0.04% | 0.32 | **passed, added** (paper from 2026-11-09 08:00 UTC) |

Notes: all three adds are cdeep_funding subsets; the family is now 14 on paper – still one bet. majors_calm has the best
half B of any pass so far (+1.00%), but it is an intersection of two filters picked from earlier results, so its history
is selected; only paper counts. lower_high adds little over plain cdeep_funding (half B +0.20% vs +0.19%); it got the
third slot over thin_bid on half B and 2x costs. The 24h hold lost at 2x costs: the edge needs time, and the
take-profit is the better exit. BTC funding as a market-wide signal lost in half B. SOL 2023-02-09 is again the worst
trade in 4 of 6 ideas; NEAR 2025-10-18 in 3. Failed ideas were not re-tuned; 6 screens unused; 3 of 3 slots used.

## 2026-11-10 (daily agent; 6 ideas, 6 screens, 3 passed, 2 added)
Theme: test why the carry edge works (no short crowding market-wide, ETH's bear as the alt bid), price events inside a
coin's own bear (daily-close breakdown, heavy-volume sell day), the calm-large-cap edge without funding, and a
take-profit on the 30-day low break. Screens: 81–86.

| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day t | result |
|---|---|---|---|---|---|---|---|
| **cdeep_funding_no_market_shorts** | <= 10% of the 19 coins have negative funding: no squeeze fuel market-wide | 245 (104/141) | +1.61% | +1.05% | +1.09% | 1.26 | **passed, added** (paper from 2026-11-10 08:00 UTC) |
| **cdeep_funding_eth_bear** | ETH in its own deep bear: no alt-rotation bid to squeeze carry shorts | 327 (110/217) | +0.38% | +0.13% | +0.02% | 0.42 | **passed, added** (paper from 2026-11-10 08:00 UTC) |
| cdeep_low_break_daily | daily close under the 30-day closing low while longs pay: swing longs cut on closes | 69 (27/42) | +1.89% | +1.55% | +1.48% | 0.26 | failed (69 trades < 100, half A 27 < 30) |
| cdeep_distribution_day | -4%/24h on 2x turnover while funding stays positive: a holder distributing into longs | 48 (26/22) | -0.96% | -2.38% | -1.81% | -0.97 | failed (48 trades, loses in both halves) |
| cdeep_majors_calm_trend | calm large cap in its own bear under a falling EMA480, daily, no funding | 440 (183/257) | +0.29% | +0.05% | -0.05% | -0.01 | failed (2x costs < 0) |
| cdeep_low_break_take | cdeep_low_break_carry entries with a 5% take-profit | 111 (49/62) | +0.59% | +0.90% | +0.57% | -0.14 | passed, NOT added (day average -0.09% <= 0) |

Notes: cdeep_funding_no_market_shorts has the best half B and 2x numbers of any pass so far (+1.05% / +1.09%), with a
filter that fits the working explanation (the carry edge is the absence of short crowding). It is still a cdeep_funding
subset, so the family is now 16 on paper – one bet. Its day t is only 1.26 (124 days). cdeep_funding_eth_bear is a weak
pass (2x costs +0.02%, half B +0.13%, below plain cdeep_funding's +0.19%); entered because it passed and the slot was
free, but it adds little. cdeep_low_break_take passed per trade but its day-weighted average is negative, which is the
kill rule on paper, and its entries are the same as cdeep_low_break_carry's; I left the third slot unused instead.
The daily-close breakdown had strong per-trade numbers but too few trades; not re-tuned. Heavy-volume sell days lost
(sellers were already done; the 2023 SOL/DOGE/UNI bounces were the worst trades), and large caps without the funding
condition lost at 2x costs: again the funding condition carries the edge, not the trend or calm. SOL 2023-02-13 is among
the worst trades in 2 ideas. 6 screens unused; 2 of 3 slots used.

## 2026-11-11 (daily agent; 6 ideas, 6 screens, 5 passed, 3 added)
Theme: test the working explanation (the carry edge = no short crowding) directly: drop the coin's own funding and keep
only the market-wide "no shorts" filter; ask BTC funding the same question; plus a wider stop, taker selling, and two
combinations with the no-shorts filter. Screens: 87–92.

| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day t | result |
|---|---|---|---|---|---|---|---|
| **cdeep_calm_shorts_trend** | own deep bear + under EMA480, <= 10% of coins with negative funding, once a day, no own-funding condition: no squeeze fuel anywhere | 245 (90/155) | +2.46% | +1.53% | +1.67% | 2.26 | **passed, added** (paper from 2026-11-11 08:00 UTC) |
| cdeep_funding_wide_stop | cdeep_funding with a 12% stop: wicks hunt 8% stops before the bleed resumes | 664 (254/410) | +0.71% | +0.14% | +0.16% | 1.41 | passed, NOT added (half B below plain cdeep_funding) |
| cdeep_funding_taker_sell | carry payers while 24h taker ratio < 0.95: sellers unloading into longs | 110 (55/55) | +0.51% | -1.00% | -0.44% | -0.22 | failed (half B < 0) |
| **cdeep_funding_btc_default** | BTC funding also at default: nobody short-hedging the market | 226 (111/115) | +0.96% | +0.82% | +0.69% | 1.64 | **passed, added** (paper from 2026-11-11 08:00 UTC) |
| cdeep_funding_no_shorts_take | no_market_shorts entries with a 5% take-profit | 247 (106/141) | +0.51% | +0.68% | +0.41% | 0.98 | passed, NOT added (take-profit lowered half B from +1.05%) |
| **cdeep_majors_no_shorts** | large caps + no market shorts: wide holder base, nothing to squeeze | 109 (48/61) | +1.89% | +1.24% | +1.33% | 1.89 | **passed, added** (paper from 2026-11-11 08:00 UTC) |

Notes: cdeep_calm_shorts_trend is the first pass without the coin's own funding condition, and it has the best numbers
so far in both halves (+1.53% half B, +1.67% at 2x, 65% wins). It supports the working explanation: the edge is the
market-wide absence of shorts, not the coin's own funding. It still overlaps heavily with cdeep_funding_no_market_shorts
(same filter), so count the no-shorts trio (no_market_shorts, calm_shorts_trend, majors_no_shorts) as one bet inside the
carry family (now 19 on paper). majors_no_shorts is an intersection of two filters picked from earlier results (109
trades), so its history is selected. btc_default points the same way from BTC's side. The wider stop and the take-profit
both made half B worse; taker-flow lost in 2024-26 like every positioning idea. SOL 2023-02-09/13 is again among the worst
trades in 4 ideas. Rule slip: the first screen command started with a needless `cd /c/quantlab` (same directory);
no effect on results, not repeated. Failed ideas were not re-tuned; 6 screens unused; 3 of 3 slots used.

## 2026-11-12 (daily agent; 6 ideas, 6 screens, 4 passed the screen, 1 passed the frequency rule, 1 added)
Theme: Michael's consistency rule (2026-11-11) – an idea must enter on >= 25% of bear days and >= 40 trades per year.
The carry family fires on ~14 entry days a year because all coins enter together at the same settlement hour, so this
run builds for frequency: staggered breakdown triggers (72h / 24h low breaks fire at different hours per coin) inside the
regimes that held up in both halves, and two ideas that drop the deep-bear filter so they can fire on shallow bear days.
Frequency check from the screen output: "days" / ~822 bear days (47.4% of the 1734 days 2022-01..2026-09, batch 1
register) and trades / 4.75 years. Screens: 93–98.

| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day avg | day t | entry days (% bear days) | trades/yr | result |
|---|---|---|---|---|---|---|---|---|---|---|
| cdeep_low_break_72h | payers' stops under the 3-day low fire coin by coin | 283 (135/148) | +0.78% | +0.15% | +0.25% | -0.31% | -0.61 | 176 (21%) | 60 | screen passed; **fails frequency** (21% < 25%); day average negative, so it would be killed on paper anyway. Not added |
| cdeep_low_break_24h | stops under yesterday's low | 487 (202/285) | +0.68% | -0.00% | +0.08% | -0.45% | -1.18 | 292 (36%) | 103 | failed (half B < 0) |
| deep_low_break_72h | BTC deep bear, payers, 3-day low break | 223 (143/80) | +2.21% | +1.27% | +1.67% | +1.32% | 1.69 | 114 (14%) | 47 | screen passed; **fails frequency** (14% of bear days). Not added |
| **bear_carry_no_shorts** | any bear day: <= 10% of coins with negative funding, coin pays >= 0.01% at settlement, under EMA480; no deep-bear filter | 813 (462/351) | +1.07% | +0.79% | +0.75% | +0.35% | 0.90 | 229 (28%) | 171 | **passed screen and frequency, added** (paper from 2026-11-12 08:00 UTC) |
| no_shorts_low_break_72h | no market shorts + 3-day low break, no own funding, no deep filter | 612 (335/277) | +1.61% | +0.69% | +0.99% | +0.20% | 0.40 | 137 (17%) | 129 | screen passed; **fails frequency** (17%). Not added |
| cdeep_low_break_72h_nofund | control: 3-day low break in a coin's own bear without the funding condition | 981 (299/682) | -0.37% | -1.21% | -1.15% | -1.13% | -3.60 | 317 (39%) | 207 | failed (loses in both halves) |

Notes: bear_carry_no_shorts is the first pass without any deep-bear filter (neither BTC's nor the coin's), and the first
that meets the frequency rule: 229 entry days (28% of bear days), 171 trades a year, 56% wins, positive in both halves
and at 2x costs. It is the U family (funding >= 0.01% under EMA480, which failed the scan) plus the market-wide
"no shorts" filter, so the filter is what turns it around; it overlaps with the no-shorts trio already on paper only on
coin-deep days. Its day t is low (0.90) and its day average (+0.35%) is far below its trade average (+0.95%): big
clusters of winners on a few days, many small-loss days. The regularity part of Michael's rule (60% of months positive,
every year positive, best 3 days <= 25% of profit, <= 16 weeks under the equity high) cannot be read from the screen
output; the paper verdict and a later replay must check it. Count it as its own bet, separate from the carry family.
The low-break control shows the breakdown alone loses heavily (-1.2% in half B over 682 trades); the funding condition
(longs still paying) is what makes the break pay. Staggered triggers did raise entry days (176 and 292 for the 72h / 24h
breaks vs ~66 for cdeep_funding) but the shorter the look-back, the worse half B: 24h breaks have no edge, and the 72h
break's day average is negative. deep_low_break_72h has the best per-trade numbers of the run (+1.3% day average) but
fires on 14% of bear days only; by the rule it is not entered and not re-tuned. SOL 2023-02-13 and XRP 2023-01-02 are
again the worst trades in 3 ideas. 6 screens unused; 1 of 3 entry slots used (the other two passes failed frequency).

## 2026-11-13 (daily agent; 6 ideas, 6 screens, 4 passed the screen, 2 passed the frequency rule, 2 added)
Theme: frequency. bear_carry_no_shorts (yesterday's pass) fires only at settlement hours and only on days when <= 10% of
the 19 coins have negative funding (~28% of bear days). This run keeps the one mechanism that holds up in 2024-26 (no
short crowding) and tests six ways to fire on more bear days: a daily version without the coin's own funding, a looser
market threshold (20%), a coin-level version (no negative settlement in 7 days), an hourly version of the same regime, a
positive definition (two thirds of coins paying >= 0.01%), and BTC's own funding as the market filter. Frequency check
as yesterday: "days" / ~822 bear days, trades / 4.75 years (needs >= 25% and >= 40/yr). Screens: 99–104.

| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day avg | day t | entry days (% bear days) | trades/yr | result |
|---|---|---|---|---|---|---|---|---|---|---|
| bear_calm_shorts_trend | any bear day, under EMA480, <= 10% of coins with negative funding, 23:00 daily, no own funding (shallow-bear cdeep_calm_shorts_trend) | 752 (353/399) | +0.61% | +1.22% | +0.73% | +0.71% | 1.33 | 109 (13%) | 158 | screen passed; **fails frequency** (13%). Not added |
| bear_carry_few_shorts | bear_carry_no_shorts with the market filter at <= 20% negative (3 coins) instead of 10% | 1292 (668/624) | +0.37% | -0.42% | -0.21% | +0.05% | 0.17 | 403 (49%) | 272 | failed (half B < 0) |
| bear_carry_no_own_shorts | coin-level: no negative settlement of the coin's own funding in 7 days, no market filter | 457 (300/157) | +0.25% | -0.05% | -0.05% | -0.33% | -0.80 | 213 (26%) | 96 | failed (half B < 0, 2x < 0) |
| **bear_carry_no_shorts_hourly** | same regime as bear_carry_no_shorts (last funding >= 0.01%, under EMA480, <= 10% negative) but live every hour; a coin re-enters as soon as its trade closes | 934 (513/421) | +1.05% | +0.58% | +0.64% | +0.29% | 0.77 | 246 (30%) | 197 | **passed screen and frequency, added** (paper from 2026-11-13 08:00 UTC) |
| bear_carry_payers_majority | >= 2/3 of the 19 coins with last funding >= 0.01% (positive "no shorts" definition), coin pays >= 0.01%, under EMA480 | 472 (353/119) | +0.18% | +1.54% | +0.32% | +0.78% | 1.35 | 103 (13%) | 99 | screen passed; **fails frequency** (13%). Not added |
| **bear_carry_btc_default** | BTC's last funding >= 0.01% as the only market filter (nobody short-hedging through BTC), coin pays >= 0.01%, under EMA480 | 884 (538/346) | +0.73% | +0.48% | +0.43% | +0.71% | 1.59 | 235 (29%) | 186 | **passed screen and frequency, added** (paper from 2026-11-13 08:00 UTC) |

Notes: the two adds are both shallow-bear carry ideas with a market-wide "no shorts" filter, so they overlap heavily
with bear_carry_no_shorts (on paper since 2026-11-12); count the three as one bet. bear_carry_no_shorts_hourly has the
same regime as bear_carry_no_shorts and only changes when the engine may enter (any hour instead of the settlement
bar): more trades (934 vs 813) and a few more entry days (246 vs 229), but half B and the day average are lower (+0.58%
vs +0.79%, +0.29% vs +0.35%); the settlement-hour entry seems to be the slightly better moment, not just a sampling
artefact. bear_carry_btc_default is the better of the two on day numbers (day average +0.71%, day t 1.59, the best
day t of any frequent pass so far) and uses a one-coin filter, so it is less sensitive to the exact count of negative
coins. Both adds meet the rule's two numbers (29–30% of bear days, 186–197 trades per year).
The two failures are the most useful results of the run: loosening the market filter from 10% to 20% negative coins
turns half B from +0.79% to -0.42% (1292 trades), so the edge sits on a sharp threshold – a caution for the whole
no-shorts family; and the coin-level version (no negative funding in the coin itself for 7 days) has no edge in half B,
so squeeze fuel is a market property, not a coin property. The daily (23:00) and payers-majority versions passed the
screen with strong half-B numbers (+1.22%, +1.54%) but fire on only 13% of bear days; by Michael's rule they are not
entered and not re-tuned. Worst trades: SOL 2023-02-09/13 again in 3 ideas, QNT 2022-11-23 in 2, DOGE 2025-10-10 (the
October liquidation wick) in bear_carry_btc_default. Regularity (60% of months positive, every year positive, best 3
days <= 25% of profit, <= 16 weeks under the high) cannot be read from the screen output; the paper verdict must check
it. 6 screens unused; 2 of 3 entry slots used.

## 2026-11-13 — engine changed deliberately: the verdict t-statistic was wrong

Not a discovery run. `bear_lab.py` was edited and every PAPER idea's `code_sha` re-frozen in the same action, so
nothing is marked ⛔ TAMPERED by a change that was intended. Recorded here because the whole point of the hash is
that no engine change goes unnoticed.

**The defect.** `summarize()` computed `t = mean / sd * sqrt(n)` over the daily means with no guard beyond
`sd > 0`. An idea with a fixed take-profit returns the same percentage on every win, so while a run has no losing
trade the spread of the daily means is about zero and t explodes. `cdeep_funding_take` (TARGET = 0.05, so every
win nets +4.8%) reported **t = 1713** on 7 trades and **t = 548** the next day. With `min_t = 2.5` the verdict
gate would have promoted it to 🟡 PASS on arithmetic rather than evidence. Three ideas on paper carry
TARGET = 0.05: cdeep_funding_take, cdeep_funding_majors_take, cdeep_low_break_take.

**The fix.** The reported t is now `min(the usual t, the one-sided sign test on daily means expressed as a z)`.
The sign test ignores how large the wins are and asks only how many independent days came out positive, which is
the most a sample can prove when every trade pays the same. `min_t` is **unchanged at 2.5** — the threshold was
not touched, only the number it is compared against.

Effect: 5 days all positive → 1.86 (was 548, now correctly below the gate) · 12 days all positive → 3.49 (can
still pass) · 40 days, 30 positive → 3.06 · a losing idea keeps its negative t. No idea had reached PASS, so no
past verdict changes; `PASSED.md` does not exist in either lab.

## 2026-11-14 (daily agent; 6 ideas, 6 screens, 5 passed the screen, 4 passed the frequency rule, 3 added)
Theme: the shallow-bear carry short with a market-wide "no shorts" filter is the only thing that holds up in 2024-26 and
meets the frequency rule (three on paper: bear_carry_no_shorts, _hourly, _btc_default). This run widens or sharpens that
regime without re-tuning its thresholds: the union of the two market filters, no trend condition (control), a one-week
trend, large caps only, the trend measured against BTC, and the no-own-funding version at every settlement hour.
Frequency check as before: "days" / ~822 bear days, trades / 4.75 years (needs >= 25% and >= 40/yr). Screens: 105–110.

| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day avg | day t | entry days (% bear days) | trades/yr | result |
|---|---|---|---|---|---|---|---|---|---|---|
| **bear_carry_either_filter** | coin pays >= 0.01% under EMA480 while <= 10% of coins negative OR BTC's last funding >= 0.01% (union of the two passed market filters) | 1122 (631/491) | +0.75% | +0.24% | +0.32% | +0.33% | -1.63 | 337 (41%) | 236 | **passed screen and frequency, added** (paper from 2026-11-14 09:00 UTC) |
| bear_carry_no_shorts_notrend | control: no shorts market-wide, coin pays >= 0.01%, no EMA480 condition | 1282 (734/548) | +1.03% | -0.07% | +0.36% | +0.74% | 0.67 | 268 (33%) | 270 | failed (half B < 0) |
| **bear_carry_no_shorts_ema168** | one-week trend (EMA168) instead of EMA480: the latest dip buyers are underwater, no shorts to squeeze | 759 (458/301) | +1.16% | +1.02% | +0.91% | +0.88% | 0.66 | 227 (28%) | 160 | **passed screen and frequency, added** (paper from 2026-11-14 09:00 UTC) |
| bear_carry_no_shorts_majors | the 8 large caps only: wide holder base, no thin float to squeeze | 441 (270/171) | +0.64% | +0.63% | +0.44% | +0.40% | 0.22 | 180 (22%) | 93 | screen passed; **fails frequency** (22% < 25%). Not added |
| **bear_carry_no_shorts_vs_btc** | coin/BTC ratio under its EMA480 (alt losing to BTC; 2024-26 money buys BTC, not alts), no shorts market-wide | 696 (395/301) | +0.98% | +0.50% | +0.57% | +0.70% | 0.33 | 224 (27%) | 147 | **passed screen and frequency, added** (paper from 2026-11-14 09:00 UTC) |
| bear_shorts_trend_8h | under EMA480, no shorts market-wide, at every settlement bar, no own-funding condition | 1359 (642/717) | +1.19% | +0.10% | +0.42% | +0.09% | -0.85 | 232 (28%) | 286 | passed screen and frequency, **NOT added** (weakest of 4 passes; 3 slots used) |

Notes: all three adds are variants of bear_carry_no_shorts (on paper since 2026-11-12), so the shallow-bear no-shorts
group is now 6 on paper – still one bet. bear_carry_no_shorts_ema168 has the best numbers of the run and the best
half B of any frequent pass so far (+1.02%, 2x +0.91%, day average +0.88%, 57% wins, 160 trades a year); the shorter
trend did not lower the edge, it raised it. bear_carry_no_shorts_vs_btc is the first pass with the trend measured
against BTC (alt_btc_bleed_carry failed at 2x without the no-shorts filter), so the filter is again what turns it
around. bear_carry_either_filter is the most frequent pass so far (41% of bear days, 236 trades a year) but the weakest
of the three adds, and its day t is negative (-1.63): the sign test says fewer than half of its 337 entry days were
positive, so the day average (+0.33%) is carried by big days; the paper verdict will most likely kill it. The same
holds for bear_shorts_trend_8h (day t -0.85, half B +0.10%), which is why it got no slot.
The two most useful results are the control and the trend_8h screen: dropping the trend condition turns half B from
+0.79% to -0.07% (548 trades), and dropping the coin's own funding condition drops half B to +0.10% (717 trades). In the
shallow bear both the trend and the coin's own paying longs are needed; the no-shorts filter alone is not enough (in a
coin's own deep bear it was, cdeep_calm_shorts_trend). Large caps alone had a solid half B (+0.63%) but only 22% of bear
days; by the rule not entered and not re-tuned. Worst trades: SOL 2023-02-13 again in 4 ideas, NEAR 2023-05-12 in 3,
WLD 2023-08-01 in 2, ENA 2024-06/07 in bear_shorts_trend_8h, DOGE 2025-10-10 in either_filter. Regularity (60% of months
positive, every year positive, best 3 days <= 25% of profit, <= 16 weeks under the high) cannot be read from the screen
output; the paper verdict must check it. 6 screens unused; 3 of 3 entry slots used.

## 2026-11-15 (daily agent; 6 ideas, 6 screens, 6 passed the screen, 1 passed the frequency rule, 1 added)
Theme: the shallow-bear carry short with the market-wide "no shorts" filter (coin pays >= 0.01%, under trend, <= 10% of
the 19 coins with negative last funding) is the only regime that holds up in 2024-26 and meets the frequency rule; six
are on paper. This run changes one thing at a time on bear_carry_no_shorts and asks what it costs in entry days: an even
shorter trend (72h, after 168h beat 480h), the coin paying for a whole day, a red day for the coin, sector breadth under
trend, the coin near its monthly low, and the no-shorts state held for 24h (a robustness test of the sharp 10% threshold).
Frequency check as before: "days" / ~822 bear days, trades / 4.75 years (needs >= 25% and >= 40/yr). Screens: 111–116.

| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day avg | day t | entry days (% bear days) | trades/yr | result |
|---|---|---|---|---|---|---|---|---|---|---|
| **bear_carry_no_shorts_ema72** | the three-day average is the newest leveraged longs' entry; under water, still paying, no short crowd to squeeze for them | 743 (465/278) | +1.21% | +1.20% | +1.01% | +1.02% | 1.42 | 218 (26.5%) | 156 | **passed screen and frequency, added** (paper from 2026-11-15 08:00 UTC) |
| bear_carry_no_shorts_persist | every settlement of the last 24h paid >= 0.01% (>= 3, none below): a day of bills with no relief bar | 479 (302/177) | +0.92% | +1.17% | +0.81% | +1.00% | 1.58 | 176 (21.4%) | 101 | screen passed; **fails frequency** (21% < 25%). Not added |
| bear_carry_no_shorts_red_day | coin's close below its close 24h earlier: longs paying on a day they also lost | 552 (323/229) | +1.35% | +1.64% | +1.27% | +0.91% | 1.47 | 185 (22.5%) | 116 | screen passed; **fails frequency** (22.5%). Not added |
| bear_carry_no_shorts_breadth | >= 60% of the 19 coins under their EMA480: no rotation bid between coins | 684 (399/285) | +0.84% | +1.03% | +0.72% | +0.37% | -0.69 | 168 (20.4%) | 144 | screen passed; **fails frequency** (20%); day t negative. Not added |
| bear_carry_no_shorts_near_low | close within 5% of the 30-day low: every long of the month under water, stops just below | 302 (184/118) | +1.81% | +2.03% | +1.70% | +0.90% | 1.57 | 131 (15.9%) | 64 | screen passed; **fails frequency** (16%). Not added |
| bear_carry_no_shorts_held_24h | the no-shorts state has held for every hour of the last 24h (three settlements) | 322 (245/77) | +0.36% | +1.23% | +0.37% | -0.09% | -0.14 | 73 (8.9%) | 68 | screen passed; **fails frequency** (9%); day average negative. Not added |

Notes: bear_carry_no_shorts_ema72 has the best numbers of any frequent pass so far: +1.20% in half B (ema168 +1.02%,
ema480 +0.79%), +1.01% at 2x costs, day average +1.02%, 57% wins, and the two halves are almost equal (+1.21% / +1.20%).
Shortening the trend window from 480h to 168h to 72h raised the edge each step without losing entry days (229 → 227 →
218), which fits the story that the newest dip buyers are the ones who sell. It is a variant of bear_carry_no_shorts (on
paper since 2026-11-12), so the shallow-bear no-shorts group is now 7 on paper – still one bet. Its worst trades are the
usual stop-outs (NEAR 2023-05-12, SOL 2023-02-13, NEAR 2025-08-05).
Every extra filter on the base regime passed the screen and most raised the per-trade average (red day +1.64% half B,
near the low +2.03%), but each cut entry days below the 25% line, so by Michael's rule none is entered and none is
re-tuned. The frequency ceiling of this regime is therefore set by the market filter, not by the coin conditions: the base
fires on ~28% of bear days and any further condition drops below 25%. The two robustness tests are mixed: the coin
paying for a whole day (persist) keeps the edge (+1.17% half B, day t 1.58) but the market state held for 24h (held_24h)
collapses to 73 entry days with a negative day average – the no-shorts state rarely lasts three settlements in a row, so
its value lies in the current reading, not in persistence. That is a caution for the group: the filter is a snapshot that
flips often. breadth has a negative day t despite +1.03% in half B: its day average (+0.37%) is far below its trade
average, so a few big days carry it. Regularity (60% of months positive, every year positive, best 3 days <= 25% of
profit, <= 16 weeks under the high) cannot be read from the screen output; the paper verdict must check it. 6 screens
unused (6 of the 12 allowed); 1 of 3 entry slots used (the other five passes failed frequency).

## 2026-11-16 (daily agent; 6 ideas, 6 screens, 5 passed the screen, 3 passed the frequency rule, 3 added)
Theme: yesterday showed the frequency ceiling of the no-shorts regime sits in the market filter (<= 10% of 19 = at most
one negative coin), not in the coin conditions. This run keeps the best base (bear_carry_no_shorts_ema72) and changes one
thing at a time: three other definitions of "no short crowd" (only the 8 large caps count; depth <= -0.01% instead of
count; share of 24h volume instead of share of coins), two other measures of "the newest buyers are under water" (one-day
EMA as the next step of the 480 -> 168 -> 72 series; the 72h VWAP, the literal average entry of the last three days'
buyers), and BTC's trend in place of the coin's own. Frequency check as before: "days" / ~822 bear days, trades / 4.75
years (needs >= 25% and >= 40/yr). Screens: 117–122.

| idea | reason | trades (A/B) | avg A | avg B | avg 2x | day avg | day t | entry days (% bear days) | trades/yr | result |
|---|---|---|---|---|---|---|---|---|---|---|
| **bear_carry_no_shorts_vwap72** | close under the 72h volume-weighted average price: every buyer of the last three days is losing, the ones still paying funding sell first | 727 (462/265) | +1.35% | +1.15% | +1.08% | +1.14% | 1.23 | 215 (26.2%) | 153 | **passed screen and frequency, added** (paper from 2026-11-16 08:00 UTC) |
| **bear_carry_no_shorts_ema24** | one-day EMA (next step of the trend-window series): today's leveraged buyers already under water | 810 (513/297) | +1.03% | +0.53% | +0.65% | +1.02% | 1.01 | 222 (27.0%) | 171 | **passed screen and frequency, added** (paper from 2026-11-16 08:00 UTC) |
| **bear_carry_no_deep_shorts** | market filter by depth: no coin with last funding <= -0.01% (shorts paying a full rate); slightly negative prints are noise, not a crowd | 808 (414/394) | +1.33% | +0.34% | +0.65% | +0.53% | 0.31 | 262 (31.9%) | 170 | **passed screen and frequency, added** (paper from 2026-11-16 08:00 UTC) |
| bear_carry_no_major_shorts | market filter counts only the 8 large caps (where hedges sit): none negative, alts may be | 683 (328/355) | +0.67% | +0.32% | +0.29% | +0.14% | -0.07 | 204 (24.8%) | 144 | screen passed; **fails frequency** (24.8% < 25%, marginal); day t negative. Not added |
| bear_carry_no_shorts_btc_trend | BTC under its 72h EMA instead of the coin's own trend: alts move with BTC, BTC's dip buyers under water = every alt long trapped | 796 (495/301) | +1.26% | +0.92% | +0.93% | +0.86% | 1.19 | 160 (19.5%) | 168 | screen passed; **fails frequency** (19.5%). Not added |
| bear_carry_no_shorts_volw | market filter weighted by 24h quote volume: coins with negative funding carry <= 10% of traded volume | 1219 (698/521) | +0.94% | -0.07% | +0.31% | +0.34% | -0.44 | 410 (49.9%) | 257 | failed (half B < 0) |

Notes: bear_carry_no_shorts_vwap72 is the best frequent pass after ema72 (+1.15% half B vs ema72's +1.20%, 2x +1.08%,
day average +1.14%, 57% wins, 26% of bear days) and it is the version with the clearest economic reading: the VWAP is
the price the last three days' buyers paid, not a smoothed close. It is a variant of bear_carry_no_shorts (on paper
since 2026-11-12), so the shallow-bear no-shorts group is now 10 on paper – still one bet. The trend-window series stops
at 72h: the one-day EMA keeps the entry days (222) but drops half B to +0.53% (72h +1.20%, 168h +1.02%); a one-day
average is too close to the price to say who is under water. It was entered because it passed both rules, but the
paper verdict should be read as the weakest member of the series.
The three market-filter redefinitions give the clearest result of the run. Every widening of the "no shorts" filter
raises entry days and lowers half B in step: count <= 10% of 19 (218 days, +1.20%) -> depth <= -0.01% (262 days,
+0.34%, day t 0.31) -> volume-weighted (410 days, -0.07%, fails). Together with the 20% count version (2026-11-13,
403 days, -0.42%) this says the edge lives on days when (almost) no coin at all pays shorts, however small the coin
and however small the rate; a single negative book anywhere is already a warning. no_deep_shorts passed and was
entered, but with half B at +0.34% it is the weakest frequent pass of the family and most likely to be killed on paper.
The large-cap-only filter was no wider (204 days, 24.8%, just under the line) and weaker (day t -0.07): hedges in the
majors are not the only squeeze fuel. BTC's trend in place of the coin's gives strong per-trade numbers (+0.92% half B)
but only 160 entry days, because on those days all 19 coins fire together (5 trades per entry day): fewer, bigger
clusters, the opposite of what the rule asks. Not re-tuned.
Worst trades: NEAR 2023-05-12 in all 6 ideas, SOL 2023-02-13 in 4, WLD 2023-08-01 in 2, NEAR 2025-08-05 and UNI
2025-06-22 in no_deep_shorts. Regularity (60% of months positive, every year positive, best 3 days <= 25% of profit,
<= 16 weeks under the high) cannot be read from the screen output; the paper verdict must check it. 6 screens unused;
3 of 3 entry slots used.
