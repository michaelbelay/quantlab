# VBreak4 by market condition — RESULT 2026-10-11
Pre-registration: `PREREGISTRATION_2026-10-11_vbreak_conditions.md` (sha256 460b43e0…). Runner: `vbreak_conditions.py`.
Numbers: `VBREAK_CONDITIONS_RESULT_2026-10-11.json`.

Fair universe: 12,505 of 20,443 recorded trades were on a coin in the point-in-time top 133 by volume
(6,161 from the 133-coin development list, 6,344 from the 280 "unseen" list).

| Cell | Trades | PF | PF 2x | Years + | 300 USDT book (that cell only) | Book DD | Verdict |
|---|---|---|---|---|---|---|---|
| **Bull-Calm** | 4,702 | **1.55** | **1.48** | 4/6 | **477.86** | **30.2%** | **PASS** |
| Bull-Wild | 2,443 | 0.98 | 0.94 | – | 268.64 | 48.4% | fail |
| Bear-Calm | 3,367 | 1.18 | 1.13 | 4/6 | 346.80 | 43.1% | fail (DD) |
| Bear-Wild | 1,993 | 0.73 | 0.70 | – | 229.60 | 51.1% | fail |
| (reported) Bull | 7,145 | 1.33 | 1.27 | 6/6 | 632.70 | 34.9% | not a registered cell |
| (reported) Bear | 5,360 | 0.99 | 0.95 | – | 270.68 | 56.8% | – |
| (reported) every condition | 12,505 | 1.18 | 1.13 | 5/6 | 829.41 | 44.0% | – |

Bull-Calm per year (trade-level USDT per 100 notional): 2021 −283 · 2022 +864 · 2023 +3,331 · 2024 +4,766 · 2025 −60 · 2026 +1,183.
Book per year: 2021 +52 · 2022 −42 · 2023 +132 · 2024 +64 · 2025 −53 · 2026 +25 (CAGR 8.8%).

Checks (reported, not gates):
- Bull-Calm on the development-list coins: PF 2.00; on the unseen-list coins (liquid at the time): PF 1.25 (2x 1.19).
  The edge survives on coins it was never built on, but smaller.
- Direction differs by coin set: dev-list coins earn on longs (PF 2.43), unseen-list coins on shorts (PF 1.66; longs 0.98).
- The book PF (1.12) is far below the trade PF: with 20 slots the book takes 1,727 of the 4,702 signals.
- Correction to earlier reports: the all-condition result on the fair universe is PF 1.18 / book 300 → 829 (DD 44%),
  not the PF 1.07 / −48% measured on the 280 unseen coins alone (small and dead coins it would never have traded).

Condition on 2026-10-10 (last completed daily close): Bull-Calm (BTC 20d +2.21%, vol 0.0192 vs median 0.0217).
Decision: Michael.
