# Bear ideas – batch 10, open interest (registered 2026-11-01, before the run; Michael: "test bear shorts with the open interest data")

Rules: `RULES_BEAR.md` + A1 (19 coins) + A2 (robustness gates). 2022-01 → 2026-09, halves A 2022-01..2024-04 /
B 2024-05..2026-09, 0.20% round trip + real funding, stop checked first, 10M USDT volume, entries on bear days only.
Nothing below changes after the run.

## Data
`data/market/oi/<COIN>.parquet` (Binance metrics archive, 5m): open interest in USDT, all-account long/short ratio,
top-trader long/short position ratio. Hourly value for a 1h bar = the last 5m row strictly before the bar's close
(time <= bar open + 55 min), so nothing after the close is used. A coin counts from its first OI row.
SMA20d = average of the last 480 1h closes. Ranks = position among the coin's own previous 720 hourly values (0 lowest).

## Ideas (all numbers fixed now)
| # | name | idea | entry (short, closed 1h bar) | stop / hold |
|---|---|---|---|---|
| O1 | leveraged_bounce | a bounce bought with new leverage gets flushed | close < SMA20d, 24h return >= +5%, OI 24h change >= +10%. One per coin per 24h | 8% / 48h |
| O2 | new_shorts_trend | price falls while OI rises: new shorts push the trend | 24h return <= -3% and OI 24h change >= +10%. One per coin per 24h | 6% / 48h |
| O3 | retail_crowded_long | retail accounts long-heavy in a falling coin | close < SMA20d, all-account long/short ratio rank >= 0.90, 7-day return < 0. One per coin per 72h | 8% / 72h |
| O4 | top_traders_short | large accounts lean short | close < SMA20d, top-trader position ratio rank <= 0.10. One per coin per 72h | 8% / 72h |
| O5 | market_leverage_build | total OI rises while BTC falls | daily close: total OI USDT of the 19 coins 7-day change >= +15% and BTC 7-day return <= 0; short every eligible coin. One event per 72h | 10% / 72h |
| O6 | covering_rally | price at a 72h high but OI falling: rally from short covering, not new buyers | close = highest close of 72h and OI 72h change <= -10%. One per coin per 24h | 8% / 48h |

Expected trades (rough): O1 ~300 · O2 ~800 · O3 ~600 · O4 ~600 · O5 ~200 · O6 ~300.

## Stated before the run
- 6 more trials (total 47 single ideas + scan + 3 discovery rules). Paper is the final judge.
- Prior is low: everything without OI failed, and the drift after bear days is upward. OI is new information though
  (it was never available for the full period before).
- O6 is the OI version of F1 covering_rally (flow proxy, 🔴), said openly.

## Result
Run 2026-11-01, `bear_oi.py`, rules unchanged. OI for all 20 coins from listing (BTC ETH ZEC SOL XRP NEAR DOGE UNI BNB
LINK ADA from 2022-01-01). All six 🔴. Trades in `batch10/`.

| # | trades (A / B) | win | avg | half A | half B | 2x | months + | w/o 10 best | fails |
|---|---|---|---|---|---|---|---|---|---|
| O1 leveraged_bounce | 624 (242/382) | 47.3% | -0.70% | -0.16% | -1.04% | -0.90% | 21/49 | -1.00% | all |
| O2 new_shorts_trend | 131 (62/69) | 33.6% | -1.45% | -0.63% | -2.18% | -1.65% | 16/45 | -2.56% | all |
| O3 retail_crowded_long | 1041 (481/560) | 46.9% | +0.19% | +0.92% | -0.43% | -0.01% | 25/53 | -0.05% | half B, 2x, months, top3, w/o10 |
| O4 top_traders_short | 1003 (242/761) | 41.9% | -0.97% | -1.16% | -0.91% | -1.17% | 8/40 | -1.16% | all |
| O5 market_leverage_build | 14 (14/0) | 35.7% | -1.36% | -1.36% | – | -1.56% | 0/1 | – | all (one event) |
| O6 covering_rally | 60 (29/31) | 50.0% | -1.32% | +0.57% | -3.08% | -1.52% | 15/27 | -2.99% | all |

Notes: the long/short ratio columns are empty in the archive for 2022, so O4 starts in 2023. O3 earned in 2022–23
(+1.53%, +0.67%) and lost in 2024–25 (-0.50%, -1.06%) – the same split as every other short.
