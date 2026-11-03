# Bear ideas – batch 5, new data and new structures (registered 2026-11-01, before the run)

Michael: "keep searching, don't stop". Rules: `RULES_BEAR.md` + Amendment A1 (19 trader coins minus 1000PEPE).
Period 2022-01 → 2026-09, halves **A 2022-01..2024-04 / B 2024-05..2026-09**, 0.20% round trip per leg + real funding,
stop checked first inside a candle, 10M USDT 24h volume, entries only on bear days. Nothing below changes after the run.

## What is new versus batches 1–4 and the scan
Everything so far was a single-coin short with a price/flow trigger. This batch uses **data not used before**
(BTC options volatility DVOL, spot vs perp taker flow) and **structures not used before** (hold the whole bear spell;
hedged pairs that earn from funding or from coin-vs-coin spread instead of from the market falling).

## Ideas (all numbers fixed now)
"Daily close" = close of the 23:00 UTC 1h bar. DVOL = `data/market/dvol/BTC.csv` daily; at a daily close of day D only
the row dated D-1 is used (no look-ahead).

| # | name | entry | exit |
|---|---|---|---|
| X1 | bear_spell_short | each coin: daily close where tomorrow is a bear day and today was not (start of a bear spell) | first daily close where tomorrow is not a bear day · stop 15% |
| X2 | dvol_rising | daily close, bear tomorrow, DVOL(D-1) / DVOL(D-4) - 1 >= +15%: short every eligible coin | 120h · stop 10% |
| X3 | dvol_complacent | daily close, bear tomorrow, DVOL(D-1) in the lowest 10% of the previous 90 rows: short every eligible coin | 168h · stop 10% |
| X4 | perp_led_rally | 17 coins with spot flow (not QNT, PUMP): 24h return >= +5%, perp buy-share-24h rank (720h) >= 0.70 and spot buy-share-24h rank <= 0.30 (rally bought with leverage, not spot). One per coin per 24h | 48h · stop 8% |
| X5 | carry_pair | at a funding time, coin (not BTC) funding >= 0.03%: **short coin + long BTC**, same size | first funding time with coin funding < 0.01%, or 168h · pair stop -10% on hourly closes |
| X6 | xs_momentum_pair | Sunday daily close, bear tomorrow: rank eligible coins by 30-day return; short the 3 weakest, each paired with a long in one of the 3 strongest (weakest↔strongest) | 168h · pair stop -15% on hourly closes |

Pair trades (X5, X6): return = short leg + long leg on the same notional, both legs' funding, **0.40% costs**
(0.80% at 2x). The long leg is a hedge inside a market-neutral pair (allowed by RULES_BEAR §1).

Expected trade counts (rough): X1 ~600 · X2 ~500 · X3 ~400 · X4 ~300 · X5 ~300 · X6 ~350.

## Gates (RULES_BEAR step 1, unchanged)
>= 150 trades and >= 50 per half · average net >= +0.30% in both halves · positive at 2x costs · >= 55% of bear months positive.

## Stated before the run
- 6 more trials (bear total 22 single ideas + 252-variant scan + 1 held-back check).
- 2026-04..09 was already used by the held-back check; this batch has **no clean final window**. A pass here goes to
  step 2 (300 USDT replay) and then paper on live data from now on – paper is the real judge.
- X1 is related to C1 (majors trend short, 🔴) and the downtrend study D0; new: all 19 coins, enter once per spell,
  exit on the spell's end, funding counted.
- X6 is related to xs_basket (bear batch 2026-10-24, 🔴, other window, no funding, wider list); new: 19 coins, pairs, weekly.
- Prior after 17 failures: most or all of these fail too.

## Result
Run 2026-11-01, `bear_batch5.py`, rules unchanged, 19 coins. Trades in `batch5/`.

| # | trades (A / B) | win | avg net | half A | half B | 2x costs | months + | verdict | fails |
|---|---|---|---|---|---|---|---|---|---|
| X1 bear_spell_short | 1477 (586 / 891) | 39.8% | -0.94% | -0.13% | -1.48% | -1.14% | 16/47 | 🔴 | halves, 2x, months |
| X2 dvol_rising | 283 (138 / 145) | 44.5% | -0.80% | -2.95% | +1.25% | -1.00% | 4/14 | 🔴 | halves, 2x, months |
| X3 dvol_complacent | 871 (352 / 519) | 53.2% | +0.88% | +2.10% | +0.05% | +0.68% | 16/30 | 🔴 | half B, months |
| X4 perp_led_rally | 260 (84 / 176) | 41.9% | -0.98% | -0.47% | -1.23% | -1.18% | 19/45 | 🔴 | halves, 2x, months |
| X5 carry_pair | 56 (34 / 22) | 60.7% | +1.09% | +2.04% | -0.38% | +0.69% | 3/7 | 🔴 | trade count, half B, months |
| X6 xs_momentum_pair | 360 (162 / 198) | 47.5% | +0.86% | +0.33% | +1.29% | +0.46% | 30/49 | 🟠 | – |

X6 by year: 2022 +1.35%, 2023 -1.49%, 2024 +2.44%, 2025 -1.13%, 2026 +3.26%. Worst pairs WLD/NEAR 2024-04-28 -21.2%,
ZEC/BNB 2026-08-16 -20.4%, ENA/ZEC 2025-11-09 -20.1% (pair stop is on hourly closes, so it can be passed).

### X6 checks (report only, `x6_check.py`)
- **Where the profit comes from:** short leg -0.20% per trade, long leg +1.46%. The shorts of the weakest coins lose;
  the profit is from holding the strongest coins in bear weeks. It is not a short strategy.
- Top 3 months (2024-09, 2026-03, 2026-09) = 84% of the profit; without the 10 best trades -0.61% per trade.
- **Step 2 (300 USDT, 6 legs of 50 USDT, hourly open P&L):** +154.3 USDT (2x costs +82.3), max drawdown -24.2%
  (2x -29.2%), worst pair -10.6 USDT (3.5% of the account) → passes step 2 → 🟡 under RULES_BEAR.
  By year: 2022 +54.8, 2023 -42.9, 2024 +72.0, 2025 -21.4, 2026 +92.8 USDT.
- 2026-04..09 was already used, so this result has no clean final window. Paper (step 3) is the judge.
