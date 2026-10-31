# Result: downtrend specialists, 2026-10-07 — 🔴 (no rule survived the fit; test window not opened)

Rules: `PREREGISTRATION_2026-10-07_downtrend.md`; hashes `downtrend/hashes.txt` (frozen before the run); script
`downtrend.py`; numbers `downtrend/fit.json`. 133 development coins, entries 2021-01..2023-12 on BTC-downtrend days,
costs 0.2% round trip + funding. The 2024-26 test window and the unseen coins were **not** used.

| Rule | Idea | Side | Trades | PF | PF 2× | Day t | 2021-22 / 2023 |
|---|---|---|---|---|---|---|---|
| D0 | short 20 biggest coins daily (pure regime bet) | short | 10920 | 0.99 | 0.89 | −0.15 | −301 / −43 |
| D1a | short 5 weakest vs BTC, 3 days | short | 1465 | 1.08 | 1.02 | 0.19 | +278 / +143 |
| D1b | same, 7 days | short | 1024 | 1.17 | 1.13 | 0.83 | +664 / +234 |
| D2a | failed bounce at 50h EMA | short | 5583 | 1.00 | 0.92 | 0.75 | −333 / +268 |
| D2b | failed bounce at 100h EMA | short | 4010 | 0.91 | 0.84 | 1.23 | −772 / −195 |
| D3a | breakdown below 20-day low | short | 1661 | 1.12 | 1.06 | −1.16 | +56 / +699 |
| D3b | breakdown + volume ≥ 2× | short | 329 | **0.24** | 0.23 | **−5.1** | −1417 / −162 |
| D4a | capitulation bounce, 24h | long | 282 | **1.69** | 1.61 | 1.54 | +566 / +50 |
| D4b | capitulation bounce, 48h | long | 282 | 0.72 | 0.69 | 0.19 | −391 / +49 |
| D5a | short negative funding, 24h | short | 3417 | 0.75 | 0.68 | **−2.59** | −1898 / −366 |
| D5b | short negative funding, 48h | short | 2823 | 0.81 | 0.75 | −1.51 | −1596 / −202 |
| D6 | short high-beta coins at start of a downtrend | short | 270 | 0.77 | 0.73 | −0.88 | −392 / +83 |

Survival needed PF ≥ 1.15, PF 2× ≥ 1.05, day t ≥ 2.5, both halves positive: **none passed**. D1b came closest
(PF 1.17, but t 0.83: profit from few days). Verified by hand: D3b trades are real (e.g. DOGE 2021-06-21 short on the
break, +12% squeeze to the stop); the simulator's P&L, stop, cost and funding were checked on a sample trade.

## What it means
- **Shorting in a downtrend does not pay by itself**: D0 (short the biggest coins every downtrend day) ≈ 0 before
  costs, negative after. Downtrends on BTC's 50-day average contain sharp rallies that eat shorts.
- **The losers point the same way**: shorting after a volume breakdown (D3b, t −5.1) and shorting negative funding
  (D5a, t −2.6) lose strongly, and the capitulation *long* for 24h (D4a) is the best number in the table. All three
  say: **in falling markets, after a violent flush with crowded shorts, price bounces within ~1 day**.
- This is a pattern found by looking at these results, so it is **not** a finding. It is a hypothesis for a new
  pre-registration, testable cleanly because 2024-26 and the unseen coins were not touched by this run.
