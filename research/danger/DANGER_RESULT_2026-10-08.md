# Danger switch study, 2026-10-08 — 🔴 switch not built

Idea (Michael, after the 2026-10-08 sell-off): skip long trades when >= 70% of coins are down over 24h.
Script `research/danger/danger_study.py`, output `study_2026-10-08.out`. Development coins only (133), 2021-01..2026-09.
Rule for "useful" fixed before running: danger trades have negative day-average AND skipping them helps in >= 4/6 years.

| Long strategy | Day avg, all | in danger (>=70% down) | normal hours | years helped by switch |
|---|---|---|---|---|
| volume absorption (incubating) | +2.13% | +2.83% | +1.10% | 2/6 |
| channel 602db68df71a | +0.49% | +0.65% | -0.16% | 0/6 |
| streak 9ef3c32f80d4 | +0.54% | +0.72% | -0.06% | 0/6 |
| long every coin 24h (baseline) | -0.11% | +0.01% | -0.19% | 2/6 |

Same picture at 60% and 80%. Danger hours are 38% of all hours.

Result: the opposite of the idea. Longs taken after a broad sell-off did BETTER than longs at other times (crypto
bounces after wide dumps; same effect as the F1 crash-bounce rule). The switch would have removed the best trades.
Not built. Caveat: channel/streak were selected on these dev data; the baseline row is the clean one.
Possible follow-up (not done): the reverse, "long only after a broad sell-off", as a discovery idea in the incubator.
