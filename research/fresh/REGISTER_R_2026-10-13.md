# Batch R - FlowTrend rule on the next tier of coins (ranks 11-30), registered 2026-10-13 before any result

Order flow in trend (F3 / FlowTrend) is the only edge found. Question: does the SAME rule, unchanged, also earn on
the coins ranked 11-30 by last month's traded value (point in time, among the 133 coins the bots trade)? If yes it is
a second, separate set of trades ("FlowTrend Mid") that can run beside FlowTrend.

- Rule frozen exactly as FlowTrend: 24h taker buy-share z (720h window) >= 2 with 10d return > 0 -> long; <= -2 with
  10d return < 0 -> short; hold 48h; stop 2 x daily move; one trade per coin per side per 24h. No setting is chosen.
- Universe R1: PIT ranks 11-30. Data: Binance 1h klines with taker volume (data.binance.vision), downloaded for the
  coins missing from user_data/flow_data.
- Account: 300 USDT, 6 slots equity/6, 1x, 0.10%/side + funding.
- Reported: 2022-2024 and 2025-01..2026-09-21 separately, per year, and R2 = one book over ranks 1-30 (FlowTrend + Mid).
Pass bar (R1, both periods because nothing is fitted): >= 30 trades, avg > 0, PF >= 1.2, account > 300 in each
period, 2025 and 2026 both positive. Running count before this batch: 52 families today.

## Results (batch_r.py -> batch_r_results.json), 2026-10-13: R1 FAIL
| set | 2022-24 | 2025-26 |
|---|---|---|
| R0 ranks 1-10 (= FlowTrend) | 1,160 trades +0.60% PF 1.29, acct 696 | 777 trades +0.61% PF 1.30, acct 532, 2025 +440 / 2026 +33 |
| R1 ranks 11-30 | 2,352 trades +0.18% PF 1.07, acct 354 drop 41% | 1,460 trades -0.05% PF 0.98, acct 193 drop 50%, 2026 -142 |
| R2 ranks 1-30 one book | +0.32% PF 1.13, acct 395 drop 53% | +0.18% PF 1.07, acct 267 |
The flow edge lives only in the 10 most traded coins; adding ranks 11-30 makes FlowTrend worse. Keeps the live
FlowTrend universe (top-10) as it is.
