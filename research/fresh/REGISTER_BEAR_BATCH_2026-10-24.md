# Bear batch - 10 new ideas, registered before the run (2026-10-24)

Michael 2026-10-24: "the market is bearish at large scales, we should find other ideas ... we have failed strategies
that maybe if we tweak it it might get better ... the roi is very small". NFI and E0V1EN are dip buyers with small wins;
nothing live earns from falling markets or makes bigger moves per trade.

## Data and costs
- Coins: the NFIFull list (220 coins, research/fresh/strat_bt/CrashShort/config.json), 1h futures candles, user_data/data_nfi.
- Period 2024-04-01 .. 2026-09-30 (same as every other test). Entry at the close of the signal candle.
- Costs: 0.20% per round trip (taker fee 0.05% + slippage 0.05%, each side). Funding not counted (stated limit).
- Exits: stop %, target %, max hold hours; stop checked before target inside a candle (worst case). One trade per coin
  at a time. No slot limit here (measures the signal itself); survivors get a 300 USDT, 6-slot old-bot test next.
- BTC bear = BTC 1h close below its 50-day (1,200 h) average, from the candle before.

## Ideas (all thresholds fixed now, never tuned after the run)
| # | name | side | entry | stop / target / hold |
|---|---|---|---|---|
| 1 | rally_short | short | coin below EMA200 and EMA50 < EMA200, RSI14 >= 70 | 5% / 6% / 48h |
| 2 | retest_short | short | coin broke >= 2% under its 7-day low in the last 24h, now back at that level (-0.5%..+2%), red candle | 4% / 8% / 48h |
| 3 | fade_breakout | short | BreakoutDay entry (new 24h high, 2x volume, +3% day) while BTC bear - inverse of the failed BreakoutDay | 4% / 4% / 24h |
| 4 | crash_bounce | long | CrashShort entry (new 24h low, 2x volume, -3% day) - inverse of the failed CrashShort | 6% / 5% / 24h |
| 5 | flush_long | long | 24h change <= -15% and RSI14 <= 20 (capitulation) | 10% / 8% / 72h |
| 6 | weak_short | short | BTC bear, coin 7d change minus BTC 7d change <= -15%, below EMA50, RSI14 40..60 | 6% / 10% / 72h |
| 7 | leader_long | long | BTC bear, coin 7d change minus BTC 7d change >= +15%, above EMA50, RSI14 50..70 | 6% / 10% / 72h |
| 8 | pump_fade | short | 24h change >= +25% and the candle closes under the previous candle's low (first crack, LUMIA type) | 8% / 12% / 72h |
| 9 | bear_rally_short | short | idea 1 only while BTC bear | 5% / 6% / 48h |
| 10 | xs_basket | long+short | every Monday 00:00 UTC rank coins by 30-day change: long the top 10, short the bottom 10, hold 7 days; variant 10b = short bottom 10 only in BTC-bear weeks | weekly |

## Pass rule (fixed now)
- **Candidate 🟡**: >= 300 trades; average net trade >= +0.30% in BOTH halves (2024-04..2025-06 and 2025-07..2026-09);
  >= 60% of months positive.
- **Bear specialist 🟡**: on BTC-bear days only, >= 100 trades in each half and average net >= +0.30% in both halves.
- Basket (10/10b): average weekly net > 0 in both halves and >= 55% of weeks positive.
- Everything else 🔴. A 🟡 is not a live strategy: next step is the 300 USDT / 6-slot old-bot backtest, then paper.

## Known limits, stated before the run
- Same 30 months as earlier tests; the two halves are the only guard against luck. 10 ideas at once: one passing by
  chance is possible, so a 🟡 must also pass the old-bot step.
- quantlab tested ~57 families on unseen data and none survived; expect most of these to be 🔴.

## Result (automatic, rules unchanged)

| # | idea | trades | win | avg net | 2024-04..25-06 | 2025-07..26-09 | months + | bear days avg (A / B, trades) | USDT @50/trade | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | rally_short | 3945 | 49.9% | 0.075% | 0.705% | -0.284% | 12/30 | 0.595% / -0.407% (756/1657) | +148 | 🔴 |
| 2 | retest_short | 10664 | 39.5% | -0.068% | 0.079% | -0.171% | 12/30 | -0.464% / -0.138% (2270/4075) | -361 | 🔴 |
| 3 | fade_breakout | 13290 | 49.2% | -0.261% | -0.035% | -0.357% | 4/26 | -0.035% / -0.357% (3952/9338) | -1737 | 🔴 |
| 4 | crash_bounce | 28661 | 49.6% | -0.372% | -0.65% | -0.169% | 11/30 | -0.45% / 0.06% (5643/9851) | -5325 | 🔴 |
| 5 | flush_long | 2199 | 56.4% | 0.149% | 0.982% | -0.628% | 17/29 | 1.329% / -0.343% (744/849) | +164 | 🔴 |
| 6 | weak_short | 6112 | 39.4% | -0.382% | -0.431% | -0.35% | 7/27 | -0.431% / -0.35% (2375/3737) | -1166 | 🔴 |
| 7 | leader_long | 7295 | 37.1% | -0.457% | -0.448% | -0.459% | 9/27 | -0.448% / -0.459% (1301/5994) | -1668 | 🔴 |
| 8 | pump_fade | 1628 | 39.4% | -0.406% | 0.663% | -0.677% | 13/30 | -1.043% / -1.013% (74/649) | -330 | 🔴 |
| 9 | bear_rally_short | 2422 | 47.9% | -0.086% | 0.598% | -0.398% | 9/26 | 0.598% / -0.398% (759/1663) | -104 | 🔴 |
| 10 xs_basket long top10 / short bottom10 | 130 weeks | 56.2% weeks + | 1.17%/week | -0.1% | 2.49% | | | | 🔴 |
| 10b short bottom10, BTC-bear weeks | 60 weeks | 43.3% weeks + | -0.63%/week | -1.59% | 0.27% | | | | 🔴 |

## Older-years check (2026-10-24, same rule, 2022-02..2024-03, 99 of the 220 coins had data)
- 10 long/short basket: +0.20%/week, 49% of weeks positive (2022-02..2023-02 -0.16%, 2023-03..2024-03 +0.53%) -> 🔴
- 10b short-only in BTC-bear weeks: +0.20%/week, 45% weeks positive (+0.68% / -0.52%) -> 🔴
- Over 2022-2026 the basket earned only from 2025-07 on; matches the 2026-09-29 rotation study (regime-bound). Not pursued.
