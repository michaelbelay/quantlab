# quantlab rules (fixed 2026-10-04, before any result)

Goal: automated **futures** strategies for a 300 USDT Binance USDT-M account. No spot.
Every strategy is **market-neutral**: at every moment the same number of longs and shorts,
with the same notional on each side. Leverage up to 5x.

## Data (read-only, from the old bot project)
| Set | Coins | Period | Use |
|---|---|---|---|
| DEV | 133 known coins (`split_140.json`) | 2021-01-01 → 2026-03-25 | research, parameter choice |
| VALID | 280 unseen coins (`oos_universe.json`) | 2021-01-01 → 2026-03-25 | one run of the chosen config, no changes |
| FINAL | all 413 coins | 2026-03-26 → 2026-09-25 | one look per family, only after VALID passes |

## Simulation (same for every family)
- 8-hour bars (00/08/16 UTC), built from 1h futures candles. Decision on data up to the bar
  close, executed at that close.
- Costs per side: fee 0.05% + slippage 0.05%. "2x costs" doubles both.
- Funding charged from the real funding history (longs pay positive rates).
- Isolated margin per position at leverage L; liquidation when the bar's high/low crosses
  entry × (1 ± (1/L − 1%)); the whole margin of that position is lost.
- 300 USDT start, compounding. Gross notional = L × equity, half long, half short.
- Eligible coin at a rebalance: ≥ 30 days of history, ≥ 10M USDT traded in the last 24h,
  position size ≥ the coin's minimum order (BTC 50, ETH/LINK/BCH/LTC/ETC 20, others 5 USDT).
  Ineligible coins are skipped and the next-ranked coin is used, so both sides stay equal.

## Gates
DEV (grid run at L = 1; leverage chosen afterwards):
- D1 profit after base costs · D2 profit at 2x costs · D3 Sharpe ≥ 1.0 · D4 max drawdown ≤ 35%
- D5 at least 4 of 6 calendar years positive (2021 … 2026Q1)
- D6 final equity above the 95th percentile of 200 random-selection twins (same k, same rebalance)
- D7 ≥ 75% of the chosen config's grid neighbours pass D1
- Selection: highest Sharpe among configs passing D1–D6.
- Leverage: the largest L in {1, 2, 3, 5} whose DEV run keeps max drawdown ≤ 35% and loses
  < 10% of equity to liquidations.

VALID (chosen config and leverage, unchanged): profit at base and 2x costs, Sharpe ≥ 0.7,
max drawdown ≤ 40%.

FINAL: profit, max drawdown ≤ 20%.

Verdict: 🟢 DEV + VALID + FINAL · 🟡 DEV + VALID · 🟠 DEV only · 🔴 fails DEV.
Only 🟢 goes to a paper forward test. No gate is changed after results are seen; a new idea
gets a new entry in FAMILIES.md before it runs.

## Amendment A1 (2026-10-05, after F9 failed VALID, before any run on the combined set)
Finding: the DEV set (133 coins) was chosen in Sept 2026 by market cap — survivors and eventual winners.
The VALID set (280) is everything else, incl. dead coins. Each alone is biased (DEV towards hindsight
winners, VALID towards losers); momentum-type signals are most exposed.
Correction: the fair universe is **ALL 413 coins together, point in time** (a coin is tradeable only while it
has data and passes the 10M/24h volume filter). Families whose DEV pass predates this amendment are re-run
**unchanged** (same config, leverage, stop) on ALL, 2021-01-01 → 2026-03-25, against the VALID gates
(profit at base and 2x costs, Sharpe ≥ 0.7, max DD ≤ 40%). Pass → FINAL on ALL, 2026-03-26 → 2026-09-25,
one look. New families from now on are developed on ALL with a time split
(DEV 2021-01 → 2024-06, VALID 2024-07 → 2026-03-25, FINAL as before).

## Protocol B — positioning data (2026-10-05, before any run)
Data: the 30 desk coins (`data/market/desk/`), 15m klines + 5m positioning (open interest,
top-trader long/short accounts and positions, all-account long/short, taker buy/sell) + funding,
2024-09-01 → 2026-09-25, as **4-hour bars**. Zero open interest = missing.
Split: DEV 2024-09-01 → 2025-08-31 · VALID 2025-09-01 → 2026-03-25 · FINAL 2026-03-26 → 2026-09-25 (one look;
positioning data never used there; prices of these coins at 8h were part of F18's FINAL — stated).
Gates as RULES.md with D5 = at least 3 of the 4 DEV quarters positive. Leverage step as RULES.md.
Forward test: any family that passes FINAL goes to a paper forward runner on live public data.

## Written vs executed — known deviations (recorded 2026-10-09 after the external assessment)
- **DEV coin list:** `quant/paths.py` uses split_140 `dev + holdout` (133 coins with data). Deliberate: the 63-70
  "holdout" coins had already been used by 7+ old-bot sweeps and were declared development data
  (`research/AMENDMENT_2026-10-04_platform.md`). They are NOT a holdout and no result may call them one.
- **FINAL window 2026-03-26 → 09-25 is SPENT:** F18 FINAL looked once, then C40 "RECENT" and C39's validation (to
  2026-04-01) used it again. Any later number on that window is in-sample. A new clean test needs a new window
  (forward paper data, or the never-mined 2017-08 → 2020-12 block where coverage allows).
- **F18** (selector) lives in `quant/selector.py`, not in the `FAMILIES` dict; F7/F8 have no `runs/*_dev.json`
  (their results are in FAMILIES.md and in the selector cache).
- **Protocol B P1–P4** were registered but never run: no result exists, none may be quoted.
- **D6 twins:** 200 per config, escalated to 2,000 when the result lands in p85–p99.5 (2026-10-09).
- **Trial count:** `python -m quant.trials` (runs/trials.json) — raw, de-duplicated and effective N for the whole project.
