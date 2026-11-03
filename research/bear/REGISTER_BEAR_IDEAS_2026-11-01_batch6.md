# Bear ideas – batch 6 (registered 2026-11-01, before the run)

Rules: `RULES_BEAR.md` with Amendments A1 (19 coins) and A2 (robustness gates). 2022-01 → 2026-09, halves
A 2022-01..2024-04 / B 2024-05..2026-09, 0.20% per leg round trip + real funding, stop checked first, 10M USDT volume,
entries on bear days only. Pair stops on hourly closes. Nothing below changes after the run.

## Why these
Batches 1–5 showed: single-coin shorts in **shallow** bears (a dip inside a bull trend) get squeezed; the shorts that
paid did so in **deep** bears / crashes. Batch 6 therefore (a) adds a **deep-bear** filter, (b) tries market-neutral
cross-section ideas where the short side has its own reason to earn.

**Deep bear (for D1, D2):** at the last daily close, BTC daily close < its 200-day average **and** the 200-day average is
lower than 20 days earlier. Daily closes before 2022 come from `data/market/dev_1h/binance/BTC_USDT-1d.feather` (spot) to
warm up the average; from 2022 the futures 23:00 bar close.

| # | name | entry | exit |
|---|---|---|---|
| D1 | deep_trend_break | deep bear + bear day: coin 1h close crosses under its 480h EMA | 168h · stop 6% |
| D2 | deep_below_50d | deep bear + bear day, daily close: coin close < its 50-day average and 50-day average falling (vs 5 days ago) | first daily close above the 50-day average, or deep bear ends · stop 12% |
| D3 | xs_reversal_pair | bear day daily close: short the 3 coins with the highest 3-day return, each paired with a long in the 3 lowest (highest↔lowest) | 72h · pair stop 15% |
| D4 | funding_xs_pair | bear day, at 00:00 UTC funding time: short the 3 coins with the highest funding, long the 3 lowest | 72h · pair stop 15% |
| D5 | alt_vs_btc_trend | bear day daily close: coin/BTC ratio closes under its 30-day ratio average (first cross in 7 days): short coin + long BTC | 168h · pair stop 12% |
| D6 | deep_rally_short | deep bear + bear day: coin 72h return >= +10% and close still under its 50-day average | 72h · stop 8% |

Expected trades (rough): D1 ~250 · D2 ~200 · D3 ~700 · D4 ~700 · D5 ~800 · D6 ~150.
Deep-bear ideas may miss the trade-count gate (>= 50 per half) if half B has few deep-bear days; that is a fail, said now.

## Stated before the run
- 6 more trials (total 29 single ideas + scan). No clean final window remains: paper is the final judge.
- D1 is the scan's closest variant (T_ema480|h168|s6, failed months / held-back) with a deep-bear filter added after
  seeing that result; this is a derived idea, said openly, and it needs the robustness gates.

## Result
Run 2026-11-01, `bear_batch6.py`, rules unchanged. All six 🔴 (step 2 not reached). Trades in `batch6/`.

| # | trades (A / B) | win | avg | half A | half B | 2x | months + | top-3-month share | avg w/o 10 best | short side | fails |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D1 deep_trend_break | 341 (139/202) | 40.8% | +0.58% | +1.62% | -0.14% | +0.38% | 10/22 | 193% | -0.39% | – | half B, months, top3, w/o10, years |
| D2 deep_below_50d | 191 (68/123) | 38.7% | +1.58% | +2.92% | +0.84% | +1.38% | 8/22 | 219% | -0.57% | – | months, top3, w/o10 |
| D3 xs_reversal_pair | 884 (402/482) | 51.0% | +0.06% | -0.10% | +0.20% | -0.34% | 25/54 | 364% | -0.36% | -0.25% | all |
| D4 funding_xs_pair | 901 (394/507) | 49.5% | -0.06% | +0.03% | -0.12% | -0.46% | 26/54 | – | -0.35% | +0.09% | halves, 2x, months, top3, w/o10 |
| D5 alt_vs_btc_trend | 98 (41/57) | 43.9% | -0.51% | -0.35% | -0.63% | -0.91% | 23/51 | – | -2.29% | -0.68% | all |
| D6 deep_rally_short | 274 (115/159) | 55.8% | +1.03% | +0.12% | +1.68% | +0.83% | 11/21 | 127% | +0.46% | – | half A, months, top3 |

D6 by year: 2022 +0.46% (109), 2023 -6.04% (6, all SOL 2023-01-01..03 squeeze), 2025 +5.19% (32), 2026 +0.79% (127).
Deep-bear days exist mainly in 2022, late 2025 and 2026; 2023–24 had almost none.
