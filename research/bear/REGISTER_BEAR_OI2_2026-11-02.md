# Bear ideas – batch 11, open interest round 2 (registered 2026-11-02, before the run; Michael: "keep searching with the OI data")

Rules: `RULES_BEAR.md` + A1 + A2. Same period, halves, costs, funding, stop-first, volume filter, bear days only, OI
timing as in batch 10 (last 5m row <= bar open + 55 min). Nothing below changes after the run.

## Part 1 – five hand-written ideas
SMA20d = 480h average of closes. Ranks vs the coin's previous 720 hourly values.

| # | name | idea | entry (short) | stop / hold |
|---|---|---|---|---|
| P1 | leverage_peak_downtrend | OI at a 30-day extreme while the coin trends down | OI rank >= 0.95, close < SMA20d, 7-day return < 0. One per coin per 72h | 8% / 72h |
| P2 | leverage_vs_activity | much open leverage for little trading | (OI USDT / 24h quote volume) rank >= 0.90, close < SMA20d. One per coin per 72h | 8% / 72h |
| P3 | trapped_longs | longs add into a falling price and pay to hold | last funding >= +0.01%, OI 72h change >= +15%, 72h return <= 0. One per coin per 72h | 8% / 72h |
| P4 | releverage_after_flush | after a flush, leverage comes back but price does not | in the last 168h OI's low was <= 0.80 × its 168h high (a flush), OI is now >= 1.10 × that 168h low, close < SMA20d. One per coin per 72h | 8% / 72h |
| P5 | weak_weekly_rally | a week-long rally with shrinking OI is short covering | 7-day return >= +5%, OI 7-day change <= -10%, close < SMA20d (480h). One per coin per 72h | 8% / 72h |

## Part 2 – OI discovery (learn on half A, test once on half B), as `REGISTER_BEAR_DISCOVERY_2026-11-01.md`
- Sample: each coin with OI at each daily close where tomorrow is a bear day (volume filter); trade = short, stop 8%, 72h.
- Features: the 25 of the first discovery **plus** OI 24h, 72h, 7-day change; OI rank (720h); OI USDT / 24h volume rank;
  all-account and top-trader long/short ranks; taker long/short volume ratio (24h mean) rank.
- Picking, half-B test, step 2: identical to the first discovery (5 buckets from half A, single and two-part rules,
  >= 100 half-A samples, avg >= +0.50%, positive in 2022 and 2023-01..2024-04, top 3 by t-stat with no shared feature;
  half B: >= 50 trades, avg >= +0.30%, > 0 at 2x, >= 55% months, > 0 without 10 best, best 3 months <= 50%).
- At least one part of each picked rule must be an OI feature (otherwise it repeats the first discovery).

## Stated before the run
- 5 + 3 = 8 trials (total 55 single ideas + scan + 6 discovery rules). Paper is the final judge.
- Prior is low after batch 10 (all six OI ideas 🔴).

## Result
Run 2026-11-02, `bear_oi2.py`, rules unchanged. All 8 🔴. Files in `batch11/`.

| # | trades (A / B) | win | avg | half A | half B | 2x | months + | w/o 10 best |
|---|---|---|---|---|---|---|---|---|
| P1 leverage_peak_downtrend | 106 (52/54) | 47.2% | +0.05% | +1.45% | -1.29% | -0.15% | 16/34 | -1.55% |
| P2 leverage_vs_activity | 1209 (444/765) | 48.6% | +0.16% | +0.34% | +0.06% | -0.04% | 23/52 | -0.01% |
| P3 trapped_longs | 76 (48/28) | 44.7% | -0.74% | -0.84% | -0.58% | -0.94% | 13/35 | -2.65% |
| P4 releverage_after_flush | 1086 (481/605) | 47.1% | -0.21% | -0.19% | -0.22% | -0.41% | 21/53 | -0.44% |
| P5 weak_weekly_rally | 99 (41/58) | 34.3% | -1.76% | -0.72% | -2.49% | -1.96% | 14/30 | -3.09% |

OI discovery: 360 rules qualified on half A; the 3 picked fail half B.
| picked on half A | half A trades / avg | half B trades / avg | B 2x | B months + | B w/o 10 best |
|---|---|---|---|---|---|
| BTC 7d -3.4%..-1.3% & long/short account rank >= 0.90 | 150 / +2.73% | 152 / -0.41% | -0.61% | 10/22 | -1.18% |
| BTC 1d >= +1.4% & OI/volume rank <= 0.17 | 165 / +3.01% | 191 / +0.73% | +0.53% | 11/22 | -0.38% (best 3 months 244%) |
| coin 7d vol lowest fifth & OI 24h >= +4.1% | 107 / +1.46% | 58 / -0.32% | -0.52% | 8/20 | -1.90% |
