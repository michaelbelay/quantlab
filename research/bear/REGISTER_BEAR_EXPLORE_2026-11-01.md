# Bear short exploration scan (registered 2026-11-01, before the run)

Michael: "find a bearish short trade ... be open to explore ideas". Rules: `RULES_BEAR.md` + Amendment A1.

## Setup (fixed now)
- Coins: BTC ETH ZEC SOL XRP HYPE NEAR DOGE UNI BNB SUI ENA QNT ARB WLD PUMP LINK ADA TAO (19; a coin counts from its
  first candle). 1h candles + funding, `data/market/main`.
- **Shorts only**, entry only on bear days (BTC 20-day return <= 0), entry at the close of the signal candle, one trade
  per coin at a time, stop checked first inside a candle, 0.20% round trip + real funding, 10M USDT 24h volume.
- **Scan window** 2022-01-01 → 2026-03-31, halves **A 2022-01 → 2023-12** and **B 2024-01 → 2026-03**.
- **Held back:** 2026-04-01 → 2026-09-30, opened once, only for the top 5 of the scan.

## Grid: 28 entries × 9 exits = 252 variants
Entries (signal on the closed 1h candle):
| family | variants |
|---|---|
| T trend cross | close crosses under EMA n, n = 24, 72, 168, 480 h |
| K breakdown | close under the lowest low of the previous N hours, N = 24, 72, 168, 480 |
| R rally fade | RSI14 falls back under X after being >= X, with close under EMA480; X = 60, 70, 80 |
| W relative weakness | at the daily close: coin 7-day return minus BTC 7-day return <= -5%, -10%, -20% (BTC itself skipped) |
| U funding | at a funding time: last funding >= 0.01%, 0.02%, 0.05% and close under EMA480 |
| D time of day | short at the close of the hour h = 00, 04, 08, 12, 16, 20 UTC (every bear day) |
| P pump fade | 24h return >= +5%, +10%, +20% (first candle of the condition) |
| V selling candle | 1h return <= -2%, -4% with volume >= 3× its 24h average |

Exits: max hold 12, 48, 168 hours × stop 3%, 6%, 12% (no target).

Null (for comparison, not a variant): a short at a random hour on bear days with the same exits, same trade count.

## Gates (fixed now)
**Scan:** >= 100 trades and >= 30 in each half · average net >= +0.30% in both halves · average net > 0 at 2x costs ·
>= 55% of months with trades positive.
**Top 5:** survivors ranked by the weaker half's average net (one variant per entry family at most, so the 5 are
different ideas). If fewer than 5 survive, only the survivors.
**Held-back check (one look):** >= 20 trades and average net > 0 at 2x costs. Passing → 🟠 → step 2 (300 USDT replay).

## Stated before the run
- 252 variants: by luck alone some will pass the scan. The held-back 6 months is the guard, and the report shows how
  many variants passed versus what the random-hour null gives.
- A "pass" is not a strategy yet: steps 2 and 3 (300 USDT replay, paper) still apply.

## Result
Run 2026-11-01, `bear_explore.py`, rules unchanged. Files in `explore/` (scan.csv = all 252, null.csv = random-hour shorts).

- **0 of 252 variants passed the scan** (random-hour null: 0 of 252). Held-back 2026-04..09 therefore **not opened**.
- Average of all variants -0.44% per trade; random bear-day shorts with the same exits -0.36%: the signals did slightly
  worse than shorting at random hours.
- Closest: **T_ema480|h168|s6** (close crosses under the 480h EMA, hold up to 7 days, stop 6%): 781 trades, +0.79% per
  trade, half A +1.36%, half B +0.50%, 2x costs +0.59% - failed only the months rule (22 of 47 months positive).
  Report-only check: by year 2022 +1.28%, 2023 +1.45%, 2024 -1.39%, 2025 +1.78%, 2026 Q1 -0.19%. The best 3 months
  (2022-05 LUNA, 2025-03, 2025-11) carry 105% of the profit; without them -0.04% per trade. It is a crash catcher:
  small losses most months, big wins in crash months. Worst trades ZEC 2025-04-06 -11.0%, ZEC 2025-04-10 -8.4%.
- U_fund0.05 (funding >= 0.05% under the 480h EMA) +1.5 .. +4.4% per trade but only 14-15 trades in 4 years.
- Verdict: 🔴 for all 252 under the registered gates.
