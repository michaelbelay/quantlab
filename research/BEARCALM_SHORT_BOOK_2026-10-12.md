# VBreak4 shorts in Bear-Calm as the 300 USDT account — 2026-10-12 (descriptive, not a gate)

Runner `bearcalm_short_book.py`, numbers `BEARCALM_SHORT_BOOK_2026-10-12.json`. Same trades / point-in-time top-133 coins /
BTC condition / book as the 2026-10-11 conditions test, cut to what the paper bot does: shorts only, Bear-Calm only,
20 slots, <= 10 shorts, stake = equity/20, 1x. The short side was chosen after seeing that test, so this describes.

| | Final (from 300) | Worst drop | Book PF |
|---|---|---|---|
| 2021-01 .. 2026-09 | 400 | 19% | 1.20 |
| costs x2 | 380 | 21% | 1.16 |
| without the 3 best trades | 334 | 24% | 1.07 |
| **without 2022** | **299** | 21% | **1.00** |

Book per year (USDT): 2021 +22 · 2022 +87 · 2023 +35 · 2024 −24 · 2025 −45 · 2026 +26.
Trade level: 2,181 trades, PF 1.32, but 2 of 6 years positive; 94% of the profit in one week (2022-05-16, LUNA crash);
the weeks 2022-01-17 and 2022-05-09 add the rest. 2024 trade-level PF 0.09 (shorts squeezed in the 2024 rallies).

Reading: the backtest edge is the 2022 crash. Outside 2022 the bear-short book is flat (300 -> 299), and the last two
full years lost. The paper forward test (C:\quantlab\FORWARD_2026-10-11_bearcalm_short.md) continues unchanged and
keeps the verdict.
