# Scanner improvement loop - idea queue (stated 2026-10-13, before testing any of them)

Michael 2026-10-13: "search why they have been failed and why others passed ... work on improving the strategies on
the loop and work on automation". Claude works this queue every 6 hours (session cron) - ONE idea per run, top first.

How an idea is judged (same bar as postmortem.py, fixed now):
- re-run every rule with the change on the scanner's cached history (live_cache, from 2026-04-20) AND on the live
  forward record (forward.db);
- "helps" only if, versus the rule as it is, history day-average is higher AND positive with day t >= 2, AND the
  live average over >= 20 signals is higher AND positive;
- the result (helps / does not) is written below with the numbers, whatever it is; an idea is tested once;
- nothing changes a live rule, badge, bot or account. A change that helps is written up for Michael to decide.
- never use the 280 unseen coins or any held-out set.

Why these ideas: the 2026-10-13 post-mortem found that most outcomes follow what the whole market does while the
trade is open (with the market: avg positive for every rule; against: negative), 9% fast stops (<= 2h), 7% near
misses (>= 70% to target, then stopped), 11% time up. Trading with BTC's prior 24h trend did NOT help (made most
rules worse on history and live).

## Queue
1. exits: target at 0.75x and stop at 1.25x the current distance (aims at near misses and fast stops)
2. confirmation entry: enter one hour later, only if that hour did not move further against the trade
3. calm market only: skip signals while BTC's 24h move is larger than its normal daily swing (|z24 BTC| > 1)
4. liquid coins only: 24h traded value above the median of the watched coins
5. half the time limit (24h rules -> 12h, 48h -> 24h)
6. fade the market-wide hours: when 6+ coins fire the same rule in one hour, skip them (vs solo 3+ tested already)

## Results
(one block per idea, newest last)

- 2026-10-13 06:2x: idea 1 coded into postmortem.py (EXIT_IDEAS, live_exits), run deferred - only 522 MB RAM free. Runs next loop or with the 06:20 daily task.
- 2026-10-13 09:2x: idea 1 (target 0.75x, stop 1.25x) - DOES NOT HELP any rule. More trades reach target (+11-15 pts) but
  the smaller win cancels it. History day-avg: better on 8 rules but still negative on all of them; only CROWD_SHORT turns
  positive (0.08 -> 0.21, t 0.5, too weak), and live it got worse there (-1.41 -> -1.71, n 52). Live got worse on 9 of 12
  rules with >= 5 signals (e.g. VOLSPIKE_UP +1.85 -> +0.85, PUMP +0.98 -> -0.51). Nothing changed. Next: idea 2.
- 2026-10-13 ~10:00: ideas 2-6 run together (ideas_test.py -> ideas_test.json; 19,663 history events, 560 live signals
  re-simulated). NONE helps: no rule turns positive on history with any of them. Closest: BRK_LO20 skip 6+ clusters /
  calm BTC (live -1.13 -> +3.3 / +3.8 but n 26 / 17, history still -0.9..-1.0 per day); CROWD_SHORT confirm entry
  (history +0.08 -> +0.49, t 0.85, live still negative). Nothing changed.
- 2026-10-13 ~10:20: idea 7 (added after 2-6: trade the opposite side). Only BRK_LO20 flips positive on both
  (history day-avg +0.60, t 1.58; live +0.93, n 60). Long check on split_140 DEV coins only, 2021-2026
  (reverse_check.py): day-avg positive in 6/6 years (t 1.87) but the per-trade average is -0.53% (crash days, many
  coins breaking lows together, lose big). Skipping clusters or BTC-crash hours does not fix it (per trade -0.2..-0.6%).
  Does not help - money is per trade. Nothing changed.
- 2026-10-13 12:1x: queue empty (ideas 1-7 done). Post-mortem re-run: 823 live signals on 8 days, 0 proposals.
- 2026-10-13 18:46: queue empty. Post-mortem re-run: 853 live signals on 8 days, 0 proposals.
- 2026-10-14 00:46: queue empty. Post-mortem re-run: 872 live signals on 8 days, 0 proposals.
- 2026-10-14 07:57: queue empty; post-mortem skipped (only 235 MB RAM free, rule is >500 MB).
