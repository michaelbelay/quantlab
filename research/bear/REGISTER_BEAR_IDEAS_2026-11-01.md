# Bear ideas – batch 1 (registered 2026-11-01, run 2026-11-01 after Michael's OK)

Rules: `RULES_BEAR.md` (bear day = BTC 20-day return <= 0; 129 coins, no memes; 2022-01 → 2026-09, halves A/B;
0.20% round trip + funding; stop checked first; steps 1 → 2 → 3; 🔴🟠🟡🟢). Nothing below is changed after the run.

## What earlier tests taught (why these ideas, and not others)
- Plain shorting in a downtrend loses to sharp relief rallies (downtrend D0, bear-calm book outside 2022).
- Shorting fresh breakdowns and negative funding loses (D3b, D5, CrashShort): crowded shorts get squeezed.
- So every idea here **waits for the rally to fail first**, **shorts where longs are crowded**, or **hedges with BTC**.

## Ideas (all numbers fixed now)
"SMA20d" = average of the last 480 1h closes. Every idea trades only when the current UTC day is a bear day.

| # | name | side | entry (on a closed 1h candle) | stop / target / max hold |
|---|---|---|---|---|
| B1 | failed_bounce | short | coin below SMA20d; its 24h high is >= 8% above its 72h low (a relief rally) and below its 7-day high (lower high); now closes under the lowest low of the previous 6 candles and >= 3% below that 24h high. One trade per coin per 24h | stop 1% above the 24h high · target 2x the stop distance · 72h |
| B2 | crowded_longs | short | coin below SMA20d, 7-day return < 0, last funding >= +0.03% per 8h (longs paying in a falling market). Checked at 00/08/16 UTC | stop 6% · no target · 48h |
| B3 | btc_drop_laggards | short | BTC falls >= 3% in 4 hours (first such hour in 12h); short the up-to-10 coins whose own 4h change is >= 2 points better than BTC's (they have not followed yet), biggest gap first | stop 4% · no target · 12h |
| B4 | beta_pair | short alt + long BTC | Monday 00:00 UTC: rank coins by 60-day beta to BTC (daily returns); for the 5 highest (beta >= 1.2) short the alt and buy BTC with the same amount. One trade = one pair; costs counted on both legs (0.40%) | pair stop -8% · no target · 7 days |
| B5 | leaders_catch_down | short | first bear day after >= 5 non-bear days: short the 10 coins with the highest 30-day return | stop 12% · no target · 5 days |
| B6 | failed_reclaim | short | coin was below SMA20d for the last 240 hours, then closed above it, and within the next 24h closes back below it | stop 1% above the highest high since the reclaim · no target · 72h |

Expected trade counts (rough, before the run): B1 ~1,000 · B2 ~2,000 · B3 ~1,500 · B4 ~500 pairs · B5 ~150-250 ·
B6 ~800. B5 may not reach 50 trades per half; then it is 🔴 by the count rule, reported anyway.

## Gates (copied from RULES_BEAR.md, step 1)
>= 150 trades and >= 50 per half · average net trade >= +0.30% in both halves (costs + funding) · positive at 2x costs ·
>= 55% of bear months positive. Passing ideas go to the 300 USDT / 6-slot replay (step 2), then paper (step 3).

## Stated before the run
- 6 ideas at once: one may pass by luck. That is why step 2 and the paper step exist. All 6 are counted as trials.
- B5 is partly inspired by the 2026-10-24 result that buying leaders in a bear lost (leader_long); said here openly.
- B6 is close in spirit to downtrend D2 (failed bounce at the 50h/100h EMA, 🔴), but uses the 20-day average, a
  10-day "below" condition and a stop above the reclaim high. Kept as a new idea, not a re-tune.
- Report: closed results worst trade first, by half and by year (2022 separately), long/short legs of B4 separately.

## Result
Run 2026-11-01, `bear_ideas.py`, rules unchanged. Coins used: 122 (no data in the file set, so not tested: HOOD, MELANIA, PAXG, SPX, USELESS, 币安人生, 龙虾). Bear days: 47.4% of 2022-01..2026-09. Trades in `batch1/`.

| # | trades (A / B) | win | avg net | half A | half B | 2x costs | funding/trade | bear months + | USDT @50/trade | verdict | fails |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 failed_bounce | 11679 (4126 / 7553) | 42.0% | -0.825% | -0.657% | -0.917% | -1.025% | -0.033% | 15/54 | -4818.1 | 🔴 | avg net < +0.30% in a half, loses at 2x costs, bear months positive < 55% |
| B2 crowded_longs | 146 (72 / 74) | 43.8% | -0.064% | 2.753% | -2.806% | -0.264% | 0.122% | 7/24 | -4.7 | 🔴 | trade count, avg net < +0.30% in a half, loses at 2x costs, bear months positive < 55% |
| B3 btc_drop_laggards | 451 (145 / 306) | 37.9% | -0.344% | -0.443% | -0.298% | -0.544% | -0.029% | 15/32 | -77.6 | 🔴 | avg net < +0.30% in a half, loses at 2x costs, bear months positive < 55% |
| B4 beta_pair | 583 (253 / 330) | 44.9% | -0.839% | -0.804% | -0.866% | -1.239% | -0.102% | 21/48 | -244.6 | 🔴 | avg net < +0.30% in a half, loses at 2x costs, bear months positive < 55% |
| B5 leaders_catch_down | 420 (230 / 190) | 42.1% | -2.07% | -0.96% | -3.412% | -2.27% | -0.007% | 13/36 | -434.6 | 🔴 | avg net < +0.30% in a half, loses at 2x costs, bear months positive < 55% |
| B6 failed_reclaim | 1076 (373 / 703) | 37.4% | 0.201% | -0.223% | 0.426% | 0.001% | -0.005% | 22/50 | +108.1 | 🔴 | avg net < +0.30% in a half, bear months positive < 55% |

By year (avg net per trade, %):

- B1 failed_bounce: 2022 -0.69 (2359), 2023 -0.10 (1052), 2024 -0.93 (2338), 2025 -1.25 (4237), 2026 -0.27 (1693) · worst: BR 2026-09-16 -130.74%, M 2026-06-25 -64.34%, MANA 2022-05-11 -55.36%
- B2 crowded_longs: 2022 -2.00 (4), 2023 -0.11 (24), 2024 +4.32 (46), 2025 -3.42 (39), 2026 -1.94 (33) · worst: DOGE 2025-10-11 -6.26%, JASMY 2022-10-25 -6.24%, XRP 2025-10-11 -6.24%
- B3 btc_drop_laggards: 2022 -0.51 (107), 2023 +0.60 (22), 2024 -0.77 (74), 2025 +0.38 (128), 2026 -0.88 (120) · worst: ZEC 2025-04-08 -5.78%, BULLA 2026-01-31 -5.49%, SENT 2026-01-31 -4.49%
- B4 beta_pair: 2022 -1.31 (122), 2023 +0.15 (95), 2024 -1.32 (111), 2025 +0.06 (145), 2026 -1.87 (110) · worst: VVV 2026-03-02 -17.06%, H 2026-06-15 -16.64%, STX 2026-09-14 -15.28%
- B5 leaders_catch_down: 2022 -1.31 (90), 2023 +0.11 (100), 2024 -3.38 (90), 2025 -3.07 (80), 2026 -3.55 (60) · worst: AXS 2026-01-23 -14.07%, CHZ 2024-10-10 -13.53%, ENA 2025-08-01 -13.19%
- B6 failed_reclaim: 2022 -0.77 (184), 2023 +0.36 (148), 2024 -0.66 (193), 2025 +0.86 (381), 2026 +0.61 (170) · worst: H 2025-12-17 -44.19%, FORM 2025-12-15 -22.83%, CAKE 2025-02-09 -19.77%

Checks (report only): sample trades B1 ADA 2022-01-22 and B6 LIT 2023-05-24 recomputed by hand from the raw candles, entry/exit/P&L match.
Squeezes: B1 has 94 trades worse than -20% (worst BR 2026-09-16, -131%: the 24h high was far above entry, price more than doubled);
without them B1 is still -0.61% per trade. B6 has 2 such trades; without them +0.26% per trade, still below the gate and negative in 2022.
Verdict: all six 🔴. Closest: B6 failed_reclaim (+0.20% per trade, positive 2023/2025/2026, but -0.77% in 2022 and 44% of bear months positive).
B4 legs: BTC long +0.45%, alt short -0.79% per pair (high-beta alts rose more than BTC in these weeks).
