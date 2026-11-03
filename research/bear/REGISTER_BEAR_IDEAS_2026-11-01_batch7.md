# Bear ideas – batch 7 (registered 2026-11-01, before the run)

Rules: `RULES_BEAR.md` + A1 (19 coins) + A2 (robustness gates). Same period, halves, costs, funding, stop-first,
volume filter, bear days only. Deep bear as in batch 6. Nothing below changes after the run.

## Why these
Batch 6: in deep bears, shorting **rallies** won 56% and stayed positive without its 10 best trades (D6); holding
shorts through the trend did not (D1, D2: profit from 3 months). Batch 7 tries (a) rally shorts that wait for the rally
to **break** first, (b) a different entry mechanic: a **limit order above the day's open** that only fills on an
intraday spike, closed the same day, (c) two deep-bear trend shorts with a per-coin trend exit.

| # | name | entry | exit |
|---|---|---|---|
| G1 | deep_trend_hold | deep + bear, daily close: coin close < its 20-day average (daily closes) | first daily close above the 20-day average, or deep/bear ends · stop 15% |
| G2 | deep_weak_short | deep + bear, Sunday daily close: short the 5 coins with the lowest 30-day return | 168h · stop 12% |
| G3 | rally_break_deep | deep + bear: the coin's 72h return was >= +8% at some close in the last 48h, and now the 1h close is under the lowest low of the previous 12h | stop: highest high of the last 72h × 1.01 · 72h |
| G4 | spike_limit_short | bear day: at 00:00 UTC a limit short at day open + 1.0 × ATR14 (daily); fills if the high reaches it | 23:00 bar close the same day · stop at open + 2.0 × ATR14 (if the fill candle also reaches the stop, it is stopped) |
| G5 | spike_limit_deep | as G4 but only on deep-bear days and the limit at open + 0.75 × ATR14 | as G4 (stop open + 1.75 × ATR14) |

ATR14 = average of the last 14 daily true ranges (daily bars built from the 1h data, last completed day).
Limit fills are at the limit price; costs 0.20% round trip as everywhere.
Expected trades (rough): G1 ~250 · G2 ~150 · G3 ~150 · G4 ~1,500 · G5 ~700.

## Stated before the run
- 5 more trials (total 34 single ideas + scan). Paper is the final judge.
- G3 and G5 are derived from D6 / the deep-bear finding of batch 6, said openly.
- Deep-bear ideas can miss "50 per half" and the 3-month share gate because deep bears are rare; that is a fail.

## Result
Run 2026-11-01, `bear_batch7.py`, rules unchanged. All five 🔴. Trades in `batch7/`.

| # | trades (A / B) | win | avg | half A | half B | 2x | months + | avg w/o 10 best | fails |
|---|---|---|---|---|---|---|---|---|---|
| G1 deep_trend_hold | 568 (220/348) | 37.1% | +0.36% | +1.27% | -0.21% | +0.16% | 8/22 | -0.40% | half B, months, top3 (390%), w/o10 |
| G2 deep_weak_short | 188 (95/93) | 46.8% | -1.01% | +0.16% | -2.21% | -1.21% | 9/22 | -2.30% | all |
| G3 rally_break_deep | 437 (174/263) | 51.5% | -0.02% | -0.06% | -0.00% | -0.22% | 10/22 | -0.51% | all |
| G4 spike_limit_short | 1233 (379/854) | 43.0% | -0.69% | -0.27% | -0.87% | -0.89% | 17/54 | -0.79% | all |
| G5 spike_limit_deep | 929 (324/605) | 45.7% | -0.48% | -0.26% | -0.60% | -0.68% | 9/22 | -0.62% | all |

Learned (report only): intraday spikes above the open keep going on these coins (G4/G5 lose in every year); deep-bear
trend holds earn only in 2022.
