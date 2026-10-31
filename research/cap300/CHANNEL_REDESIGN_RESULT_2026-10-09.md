# Channel UP_HIVOL redesign for 300 USDT, 2026-10-09 — 🔴 no design qualifies (dev), unseen not opened

Script `channel_redesign.py` (13 designs + choice rule in its docstring, hash `channel_redesign.sha256`, fixed before
running), output `channel_redesign.out` / `.json`. Rule: median > 300, >= 4/6 years positive, median DD < 40%.

Data fix found first: `channel_sim.py` (and the unseen3 channel row) counted ~4,600 phantom fee-only trades on
frozen-price (delisted/halted) unseen coins. DEAD filter added; dev coins had 0 such trades.

| Design (dev coins) | Final median | DD median | Years + |
|---|---|---|---|
| B  K5 random (baseline) | 431 | 59% | 3/6 |
| S  K10 / K15 / K20 / K30 random | 459 / 486 / 518 / 577 | 55 / 53 / 52 / 47% | 3 / 3 / 4 / 4 |
| P  K5 liquid / calm / score | 352 / 322 / 446 | 66 / 63 / 62% | 2 / 3 / 2 |
| P  K20 liquid / calm / score | 548 / 493 / 535 | 52 / 53 / 56% | 4 / 3 / 3 |
| C  K20 max 5 new/day | 415 | 53% | 5/6 |

What it shows:
- More, smaller slots help steadily (431 -> 577, DD 59% -> 47%): the slot-blocking diagnosis was right.
- Priority inside the hour (liquid/calm/score) does not help at K5; small gain at K20 liquid.
- Drawdown is the blocker in EVERY design (47-66%) and 2024 loses in every design: all positions are altcoin longs
  opened on the same wild-uptrend days, so they fall together. Slot rules cannot fix that; exposure can.
Next redesign to test: cut gross exposure (e.g. K20-30 at 50% of equity, or a book-level stop) — must respect the
5 USDT min notional (K30 at 50% = 5 USDT per position, too tight). Unseen coins still unopened for this round.
