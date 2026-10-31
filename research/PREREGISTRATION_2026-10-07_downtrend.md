# Pre-registration: downtrend specialists, 2026-10-07

Approved direction: Michael, 2026-10-07 ("ok good start building it"), after the regime-switch test
(`REGIME_SWITCH_RESULT_2026-10-07.md`) found no strategy in the 284-candidate pool that qualified for BTC downtrends.
Written before any of the rules below was run on any data. This text and `research/downtrend.py` are hashed into
`research/downtrend/hashes.txt` before the first run; the fit survivors are hashed before the test window is read.

## Question
Rules built **for** falling markets: when BTC is in a downtrend, does any of them make money after costs and funding
on new data, where doing nothing (cash) earns 0?

## Market filter (same definition as the regime-switch test, unchanged)
BTC daily close vs its 50-day average → `DN` when below. Volatility type (`DN_LOVOL` / `DN_HIVOL`) is reported
but **not** used to select (both down types pooled; fewer trials). Known at the previous daily close. A rule may
**enter** only on a `DN` day; open trades keep their own exits when the type changes.

## Common trade mechanics
- 1h candles, Binance USDT-M futures. Signal at a bar's close, entry at the next bar's open.
- Costs: 0.10% per side (fee + slippage), the same as the engine. Funding: every settlement inside the holding
  period is charged/credited on the position (shorts receive positive funding, pay negative funding).
- `σ` = the coin's 20-day standard deviation of 24h returns (from hourly closes, 480 bars). Stop = entry × (1 ± k·σ).
  The stop is checked on each bar's high/low; if hit, the exit is at the stop price plus 0.05% slippage.
  Otherwise the exit is at the close of the last holding bar.
- One open trade per coin per rule (no stacking). P&L in % of notional per trade (notional 100 ⇒ P&L units).

## The 12 rules (fixed, no tuning)
| ID | Idea | Signal (on a DN day) | Side | Hold | Stop k |
|---|---|---|---|---|---|
| D0 | Pure regime bet | 00:00 UTC each DN day: the 20 coins with the highest 30-day dollar volume | short | 24h | 2.0 |
| D1a | Weakest keep falling | 00:00 UTC each DN day: the 5 coins with the lowest 7-day return minus BTC's | short | 72h | 1.5 |
| D1b | same | same | short | 168h | 2.0 |
| D2a | Failed bounce | coin close < its 480h average; the bar's high touched the 50h EMA from below and the bar closed below it, red | short | 48h | 1.5 |
| D2b | same | same with the 100h EMA | short | 48h | 1.5 |
| D3a | Breakdown | close below the lowest low of the previous 480 bars | short | 72h | 1.5 |
| D3b | same + volume | D3a and 24h volume ≥ 2× its 30-day average | short | 72h | 1.5 |
| D4a | Capitulation bounce | 24h return ≤ −2.5σ and 24h volume ≥ 3× its 30-day average | long | 24h | 1.5 |
| D4b | same | same | long | 48h | 1.5 |
| D5a | Negative funding continues | last funding < 0 and in the bottom 5% of its last 90 days (same as scanner FUND_LO) | short | 24h | 1.5 |
| D5b | same | same | short | 48h | 1.5 |
| D6 | High beta first | the first DN day after an UP day, at 00:00 UTC: the 10 coins with the highest 60-day beta to BTC (daily returns) | short | until the first UP day or 14 days | 2.0 |

Coins with < 60 days of history at the signal are skipped. 12 configurations = 12 trials (plus the 1136 of the
regime-switch test on related data, recorded).

## Fit (133 development coins, entries 2021-01-01 .. 2023-12-31, DN days only)
A rule survives if **all** hold:
- ≥ 100 trades; PF ≥ 1.15; PF ≥ 1.05 with an extra 0.2 per trade (2× costs);
- day-weighted t ≥ 2.5 (trades of one entry day averaged first; t = mean / sd × √days). With 12 rules, ~0.07 would
  pass by luck;
- positive in both fit halves (2021-22, 2023) that have ≥ 20 trades.

The survivors are written to `downtrend/fit.json` and hashed before any test-window trade is computed.

## Test A (same coins, entries 2024-01-01 .. 2026-09-18, DN days only)
Every fit survivor is tested; a survivor passes if **all** hold:
- A1 PF ≥ 1.10 and PF ≥ 1.00 at 2× costs;
- A2 day-weighted t ≥ 2.0;
- A3 positive in ≥ 2 of 3 periods (2024, 2025, 2026-01..09);
- A4 random baseline (information **and** gate): 1000 replicas with the same number of trades per DN day, random coins
  and random entry hours on those days, same side, hold and stop. Real total ≥ the 95th percentile. A rule that only
  matches random shorting on DN days is a regime bet; D0 is that bet, and it is judged on A1-A3 only.

## Test B (280 unseen coins, on-purpose use pre-registered here), entries 2024-01-01 .. end of their data (2026-08-31)
Only for rules that pass A. Same checks A1-A4 (A4 not for D0).

## Decision
| Result | Class | Next |
|---|---|---|
| no fit survivor | 🔴 | recorded: no downtrend specialist among these 12 ideas |
| fails A | 🔴 | recorded with the failing checks |
| passes A, fails B | 🟠 | recorded; no forward test |
| passes A and B | 🟡 | 300 USDT simulation (`research/cap300/sim.py`, DD ≤ 40%), then paper forward test; slot in the switching book for DN days. 🟢 never before forward test |

No re-run with other parameters, holds, stops or market definitions after a result is seen. A change is a new
pre-registration. Reported for every rule regardless of outcome: fit and test trades, PF, t, per-year, and the same
rule on UP days (information only, to show whether it is a downtrend specialist).

## Data rules
Development coin futures files, BTC daily file, the 280 unseen coins only in test B. Not read: the sealed desk
quadrant, out-of-time 2017-20 data.
