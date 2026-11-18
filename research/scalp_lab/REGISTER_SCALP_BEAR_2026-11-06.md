# Bear-day scalps batch 1 – registered before any screen (2026-11-06)

Engine and screen rules: SCALP_LAB.md (fixed). 19 coins, 5m, bear days only, 0.14% round trip, 2x-cost check.
ATR = 14-bar ATR on 5m at the signal bar. Each rule is screened once in the form below; no re-tuning. A changed rule
is a new file name and counts as a new screen.

| # | file | side | signal (on a closed 5m bar) | stop / target / max hold | reason |
|---|---|---|---|---|---|
| 1 | flush_exhaust_long | long | close-to-close drop >= 3 ATR, volume >= 6x 24h mean, close in the top 40% of the bar | 1.5 / 1.5 ATR / 12 bars | liquidation cascade: forced sellers done, the wick shows buyers absorbing |
| 2 | btc_lag_short | short | BTC down >= 0.6% in 15 min while the coin is down < 0.2% (not BTC itself) | 1.0% / 0.8% / 12 bars | alts reprice after BTC with a lag as market makers hedge |
| 3 | vwap_reject_short | short | below 24h VWAP 1h and 2h ago, 24h EMA falling, bar touches VWAP and closes red below it | 1.5 / 2.0 ATR / 24 bars | trapped intraday longs sell at break-even at VWAP |
| 4 | breakdown_go_short | short | close below the prior 4h low, volume >= 3x 24h mean, close in the bottom 25% of the bar, below VWAP | 1.2 / 2.0 ATR / 24 bars | stops under the 4h low fire in a cascade |
| 5 | rally_fade_short | short | +2.5% in the prior hour while down on 24h, RSI(14) >= 75 on the prior bar, red bar closing under the prior low | 2.0 / 2.0 ATR / 36 bars | bear rallies are short covering; when covering stops there is no buyer |
| 6 | reclaim_trap_long | long | new 24h low in the last 6 bars, then a close back above the broken low | 1.5 / 2.0 ATR / 24 bars | shorts who sold the breakdown are trapped and must buy back |

Related forms already tested elsewhere: #4 is close to S3 (12-bar breakout, all days, both sides, 2026-10-29), #6 is
the long mirror of bear B6 (1h). Both are kept because the bear-day filter and 5m form are new; noted here so a pass
is read with that in mind.

## Results (2026-11-06, screens 1-6, rules unchanged): 0 of 6 pass

Bear days 2024-02 → 2026-09: 522 of 973 days (48% of bars).

| rule | trades (A/B) | avg net | half A | half B | 2x costs | win | day t | result |
|---|---|---|---|---|---|---|---|---|
| flush_exhaust_long | 28 (17/11) | -0.35% | -0.30% | -0.42% | -0.49% | 39% | -1.75 | 🔴 too few, loses |
| btc_lag_short | 1855 (1152/703) | -0.17% | -0.19% | -0.14% | -0.31% | 51% | -4.74 | 🔴 |
| vwap_reject_short | 6056 (2334/3722) | -0.13% | -0.16% | -0.12% | -0.27% | 43% | -8.62 | 🔴 |
| breakdown_go_short | 6622 (2740/3882) | -0.13% | -0.14% | -0.13% | -0.27% | 39% | -10.0 | 🔴 |
| rally_fade_short | 284 (146/138) | -0.09% | -0.12% | -0.07% | -0.23% | 52% | -2.00 | 🔴 |
| reclaim_trap_long | 6147 (2484/3663) | -0.13% | -0.12% | -0.13% | -0.27% | 43% | -0.61 | 🔴 |

Why they fail (report only, no re-tune): before costs the four big rules average about +0.01% a trade, i.e.
no edge at all; the 0.14% cost is the whole loss. 5m moves of 1-2 ATR on these 19 coins are noise at taker cost.
Same lesson as the 2026-10-29 scalp test, now also on bear days only. Nothing alerts from this batch.
