# FlowTrend on bear days (2026-11-01, description only – not a new trial, nothing tuned)

Michael: "focus on our coin list". FlowTrend = the paper trader's strategy, its own signal code (`trader/flowtrend.py`),
its 20 coins (`trader/settings.py`, incl. 1000PEPE as traded). Every signal 2022-01 .. 2026-09 simulated on its own
(no slot limit): next-open entry, FlowTrend stop, 48h exit, 0.20% round trip + real funding. Bear day = RULES_BEAR.
Script `flowtrend_bear_split.py`, trades `batch4/flowtrend_trades.csv`.

| side, day type | trades | avg net | win | half A 2022-01..24-04 | half B 2024-05..26-09 |
|---|---|---|---|---|---|
| long, not bear | 488 | +0.78% | 47.7% | +0.47% | +1.10% |
| short, not bear | 549 | +0.60% | 50.6% | -0.35% | +1.46% |
| long, bear | 355 | -0.07% | 45.4% | +0.02% | -0.14% |
| short, bear | 501 | -0.03% | 46.3% | +0.50% | -0.56% |

By year, short on bear days: 2022 +0.75%, 2023 +0.16%, 2024 -0.76%, 2025 -0.10%, 2026 -0.64%.
Worst bear-day trades: ENA 2024-05-05 -19.6% (short), XRP 2024-12-20 -18.2% (short), ENA 2025-03-10 -17.2% (long).

Reading: FlowTrend's whole edge since 2022 comes from non-bear days, in both directions. On bear days it is about zero
before slot effects (856 trades, ~-0.05% each) - the same picture as the 16 bear ideas. This was found by looking, so
"pause FlowTrend on bear days" is a hypothesis: it needs its own register and a forward paper run before any change.
