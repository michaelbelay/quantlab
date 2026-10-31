# Channel UP_HIVOL (602db68df71a) in a 300 USDT account, 2026-10-09 — 🔴 not usable

Script `channel_sim.py` (rules in its docstring, fixed before running; one crash fix before any output, see .sha256),
output `channel_sim.out`. Unseen coins = main.

| Data | Slots | Final (median of 20) | Range | Max DD (median) | Taken / signals | Win | Years + |
|---|---|---|---|---|---|---|---|
| Unseen | 5 (main) | 330 | 213..732 | 60% | 1107 / 12399 | 27% | 2/6 |
| Unseen | 3 | 317 | 107..734 | 64% | 727 | 23% | 3/6 |
| Unseen | 10 | 408 | 287..575 | 52% | 2061 | 29% | 4/6 |
| Dev (in-sample) | 5 | 431 | 275..650 | 59% | 446 / 4508 | 65% | 3/6 |

Pre-set rule (median > 300, >= 4/6 years positive, DD < 40%): NO, on every setting.

Why: losers are stopped within ~1 hour (median), winners run ~45 hours. In a small account the winners block the
slots and the freed slots keep refilling with fresh signals, so the account takes far more of the quick losers
(win rate 27% vs 43% for all trades). The edge only exists when you take ALL ~26 trades a day — a large-account
property. Max drawdown 50-60% would hit the live halt rail (180) in every setting.
Status: 🟡 research lead on the whole universe, 🔴 for the 300 USDT account. Keeps incubating (unchanged).
