# Bear ideas – batch 2 (registered 2026-11-01, run 2026-11-01 after Michael's OK)

Rules: `RULES_BEAR.md`, unchanged (bear day = BTC 20-day return <= 0; same 122 coins with data; 2022-01 → 2026-09, halves
A 2022-01..2024-04 / B 2024-05..2026-09; 0.20% round trip + funding; stop checked first; gates and 🔴🟠🟡🟢 as written).
Nothing below is changed after the run.

## What batch 1 taught
- Short trades with fixed 12–120h holds lost: bear markets bounce hard (B1 had 94 trades worse than -20%; even in bear
  weeks BTC rose +0.45% on average in B4).
- So batch 2 tries the other way round: **ride the trend longer with a trailing exit** (C1, C2), short only **after the
  whole market's bounce fails** (C3), fade **thin-liquidity weekend pumps** (C4), and the **majors only**, where squeezes
  are smallest (C1, C5).

## Ideas (all numbers fixed now)
"Daily close" = close of the 23:00 UTC 1h bar. Every entry needs a bear day and the 10M USDT 24h volume filter.

| # | name | side | entry | exit |
|---|---|---|---|---|
| C1 | majors_trend_short | short | BTC, ETH, BNB each: at a daily close where the coin's own 20-day return <= 0 (mirror of the live MajorsTrend long rule) | at the first daily close where its 20-day return > 0 or the day is no longer bear · hard stop 10% · max 30 days |
| C2 | breakdown_trail | short | daily close below the lowest low of the previous 20 days | trailing stop 2 × ATR14 (daily) above the lowest close since entry, first stop entry + 2 × ATR14 · max 30 days |
| C3 | market_rally_fail | short | BTC up >= 5% over 72h, then the first 1h close of BTC below its 24h average; short the 10 coins with the biggest 72h gain. One event per 72h | stop 8% · no target · 72h |
| C4 | weekend_pump_fade | short | Monday 00:00 UTC: coins up >= 8% from Saturday 00:00 while BTC is up < 3% over the same weekend | stop 8% · no target · 72h |
| C5 | session_short | short | BTC and ETH at 13:00 UTC (US session open) | close at 21:00 UTC · stop 3% |

Expected trade counts (rough, before the run): C1 ~300 · C2 ~1,500 · C3 ~400 · C4 ~600 · C5 ~1,600.

## Gates (RULES_BEAR.md, step 1)
>= 150 trades and >= 50 per half · average net trade >= +0.30% in both halves (costs + funding) · positive at 2x costs ·
>= 55% of bear months positive.

## Stated before the run
- 5 ideas, counted as 5 more trials (batch 1 + 2 = 11).
- C2 is related to downtrend D3a (break of the 20-day low, fixed hold, 2021–23, PF 1.12, 🔴). New here: a trailing
  ATR exit, the bear-day rule of RULES_BEAR and the 2022–26 window. Said openly.
- C1 is the mirror of a live long rule; it is related to downtrend D0 (short the 20 biggest coins, PF 0.99, 🔴), but
  uses each coin's own trend, 3 majors and exits on the trend flip.
- C5 needs +0.30% per trade on BTC/ETH in 8 hours; that is a high bar for majors. Expected 🔴, cheap to check.
- Report: worst trade first, by half and by year (2022 separately).

## Result
Run 2026-11-01, `bear_ideas2.py`, rules unchanged, same 122 coins. Trades in `batch2/`.

| # | trades (A / B) | win | avg net | half A | half B | 2x costs | funding/trade | bear months + | USDT @50/trade | verdict | fails |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 majors_trend_short | 326 (160 / 166) | 31.9% | -0.645% | -0.813% | -0.482% | -0.845% | 0.012% | 14/51 | -105.1 | 🔴 | avg net < +0.30% in a half, loses at 2x costs, bear months positive < 55% |
| C2 breakdown_trail | 2062 (761 / 1301) | 34.5% | -2.378% | -0.668% | -3.378% | -2.578% | -0.086% | 11/50 | -2451.6 | 🔴 | avg net < +0.30% in a half, loses at 2x costs, bear months positive < 55% |
| C3 market_rally_fail | 500 (210 / 290) | 43.4% | -0.717% | -1.99% | 0.205% | -0.917% | -0.042% | 11/30 | -179.2 | 🔴 | avg net < +0.30% in a half, loses at 2x costs, bear months positive < 55% |
| C4 weekend_pump_fade | 369 (122 / 247) | 39.8% | -1.137% | -1.965% | -0.729% | -1.337% | -0.15% | 14/44 | -209.9 | 🔴 | avg net < +0.30% in a half, loses at 2x costs, bear months positive < 55% |
| C5 session_short | 1642 (762 / 880) | 42.0% | -0.141% | -0.207% | -0.085% | -0.341% | 0.004% | 16/54 | -116.2 | 🔴 | avg net < +0.30% in a half, loses at 2x costs, bear months positive < 55% |

By year (avg net per trade, %):

- C1 majors_trend_short: 2022 -0.63 (89), 2023 -0.53 (45), 2024 -1.75 (65), 2025 -0.64 (77), 2026 +0.64 (50) · worst: BNB 2022-11-15 -11.09%, BNB 2022-05-18 -10.64%, BNB 2022-01-22 -10.49%
- C2 breakdown_trail: 2022 -0.04 (410), 2023 +0.12 (277), 2024 -3.56 (344), 2025 -4.96 (727), 2026 -0.29 (304) · worst: H 2026-06-09 -500.52%, Q 2025-10-11 -77.77%, JASMY 2022-05-12 -53.04%
- C3 market_rally_fail: 2022 -1.93 (150), 2023 -0.80 (30), 2024 -2.36 (130), 2025 +1.63 (110), 2026 +1.03 (80) · worst: H 2026-06-14 -10.04%, PIEVERSE 2025-12-04 -8.84%, VVV 2026-03-03 -8.67%
- C4 weekend_pump_fade: 2022 -3.76 (54), 2023 -4.84 (20), 2024 +1.35 (72), 2025 -0.69 (141), 2026 -1.45 (82) · worst: PIEVERSE 2025-12-08 -10.49%, VVV 2026-02-16 -9.82%, M 2025-09-01 -9.5%
- C5 session_short: 2022 -0.19 (408), 2023 -0.14 (268), 2024 -0.29 (286), 2025 +0.01 (418), 2026 -0.15 (262) · worst: ETH 2022-04-25 -3.22%, ETH 2022-09-07 -3.22%, ETH 2022-05-26 -3.21%

Checks (report only): C2 DOT 2025-08-01 recomputed by hand (close 3.545 under the 20-day low 3.618, stop 3.947 = entry + 2 ATR, hit 08-08) - matches.
Losses beyond -100% (a 1x short is liquidated at -100% in reality): C2 1 trade (H 2026-06-09, -501%), batch 1 B1 1 trade. Capped at -100%:
C2 -2.18% per trade, B1 -0.82%; no verdict changes. C2 median trade -5.7%: the trailing stop is hit in 1,817 of 2,062 trades.
Verdict: all five 🔴. C3 earned in half B (+0.21%, 2025 +1.63%, 2026 +1.03%) but lost -1.99% per trade in half A.
