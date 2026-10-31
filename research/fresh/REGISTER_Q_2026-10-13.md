# Batch Q - cross-sectional anomalies from the crypto asset-pricing literature, registered 2026-10-13 before any result

Effects reported in academic crypto cross-section studies (lottery/MAX effect, idiosyncratic volatility, skewness,
abnormal volume/attention). Never tested in this project in this form.

Universe: point-in-time top-30 by last month's traded value among the coins in the old-bot futures folder (the
133 coins the bots trade, dead ones included), stablecoins/indices excluded. Daily bars built from 1h futures data,
funding paid. Rebalance every Monday 00:00 UTC using data up to Sunday's close. Equal notional per leg, 1x,
account = 300 USDT split equally over all legs (6 or 10 positions). Cost 0.10%/side per leg per rebalance (all legs
closed and reopened - conservative). FIT 2022-01..2024-12 (setting chosen on fit account), TEST 2025-01..2026-09-21.

| id | sort variable (past L days) | book |
|---|---|---|
| Q1 | MAX: highest single-day return | long the N lowest-MAX, short the N highest-MAX |
| Q2 | idiosyncratic vol: sd of daily residual vs BTC (beta from the same window) | long N lowest, short N highest |
| Q3 | skewness of daily returns | long N lowest, short N highest |
| Q4 | abnormal volume: 7d traded value / previous 60d average | long N highest, short N lowest |
| Q5 | low-vol long-only: N lowest total-vol coins, only while BTC 20d return > 0 (else cash) | long only |

Grid: L [30, 60] days (Q4 fixed 7/60), N [3, 5], hold [7, 14] days (14 = rebalance every other Monday).
Pass bar: TEST avg weekly-equivalent return > 0, test account > 300, 2025 and 2026 both positive, FIT account > 300,
at least half of the grid positive on test, test max drop <= 35%. No unseen/held-out coin sets.
Running count before this batch: 47 families today.

## Results (batch_q.py -> batch_q_results.json), 2026-10-13: none pass
| family | chosen (L,N,hold) | fit account | test account | test years (USDT) | grid+ |
|---|---|---|---|---|---|
| Q1 MAX effect | 60,3,14 | 423 drop 36% | 218 drop 66% | 2025 +150, 2026 -232 | 0/8 |
| Q2 idiosyncratic vol | 60,3,7 | 425 drop 44% | 102 drop 74% | -17, -181 | 0/8 |
| Q3 skewness | 60,3,14 | 352 drop 36% | 350 drop 35% | +122, -72 | 4/8 |
| Q4 abnormal volume | 7,3,7 | 342 drop 46% | 162 drop 57% | -59, -79 | 0/4 |
| Q5 low-vol long-only | 30,3,14 | 867 drop 36% | 296 drop 21% | +50, -54 | 1/8 |
2026 negative for all five; the literature effects do not hold on the liquid top-30 recently.
