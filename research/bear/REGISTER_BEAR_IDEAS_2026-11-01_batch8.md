# Bear ideas – batch 8, intraday breakdown shorts (registered 2026-11-01, before the run)

Rules: `RULES_BEAR.md` + A1 + A2. Same period, halves, costs, funding, volume filter, bear days only. Nothing changes after.

## Why
Batch 7 (G4/G5): limit shorts above the day's open lost in every year – intraday spikes keep going. If intraday moves
continue, the short side of that is a **stop-entry short on an intraday breakdown**, closed at the end of the same day.

Day = 00:00–23:59 UTC; open = 00:00 bar open; ATR14 = mean daily true range of the last 14 completed days.
Stop-entry fill: at the trigger, or at the bar's open if the bar opens below the trigger (gap). If the fill bar also
reaches the stop, the trade is stopped (worst case). Exit at the 23:00 bar close. One trade per coin per day.

| # | name | trigger (short) | stop | days |
|---|---|---|---|---|
| H1 | open_break | price falls to open − 0.75 × ATR14 | open | bear days |
| H2 | open_break_deep | as H1 | open | deep-bear days only |
| H3 | range_break | after 04:00: price falls under the 00:00–03:59 low (if that range < 1 × ATR14) | 00:00–03:59 high | bear days |
| H4 | prev_low_break | price falls under the previous day's low (only if today's open is above it) | previous day's close | bear days |

Expected trades (rough): H1 ~2,500 · H2 ~1,200 · H3 ~3,000 · H4 ~3,000.

## Stated before the run
- 4 more trials (total 38 single ideas + scan + 3 discovery rules). H1/H2 come from the G4/G5 result, said openly.
- Paper is the final judge.

## Result
Run 2026-11-01, `bear_batch8.py`, rules unchanged. All four 🔴, losing in every year.

| # | trades (A / B) | win | avg | half A | half B | 2x | months + |
|---|---|---|---|---|---|---|---|
| H1 open_break | 2378 (926/1452) | 36.3% | -0.83% | -0.56% | -1.00% | -1.03% | 10/53 |
| H2 open_break_deep | 937 (377/560) | 37.0% | -0.55% | -0.10% | -0.86% | -0.75% | 5/22 |
| H3 range_break | 8561 (3271/5290) | 36.7% | -0.31% | -0.35% | -0.28% | -0.51% | 11/54 |
| H4 prev_low_break | 5824 (2173/3651) | 21.4% | -0.66% | -0.68% | -0.64% | -0.86% | 4/54 |

### Why every short fails (report only, equal-weight 19 coins, from each daily close)
| regime at the close | forward 24h A / B | forward 72h A / B | forward 168h A / B |
|---|---|---|---|
| bear, not deep | +0.01% / +0.35% | +0.12% / +0.90% | +0.55% / +1.73% |
| deep bear | -0.12% / +0.08% | -0.24% / +0.12% | -0.44% / +0.50% |
| not bear | +0.08% / +0.03% | +0.14% / +0.22% | +0.35% / +0.53% |
After a bear day the coins **rose** on average; they fell only in deep bear in 2022. Shorts fight that drift.
