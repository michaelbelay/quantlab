# CAP300: out-of-time test of single-asset trend on majors (pre-registered 2026-10-04)

## Why
Round 2 deploy form (development coins, 2021-26): SA-L-W on BTC/ETH/SOL turned 300 → 1,125 USDT (CAGR +26%, DD 46%);
SA-LS-W 300 → 1,074. Majors are development coins, so that cannot validate itself. Every piece of research in this
project used 2021 onward; **August 2017 – December 2020 has never been touched.** It includes the 2018 crash.

## Data
Binance public archive, spot daily klines (no key): BTCUSDT, ETHUSDT, BNBUSDT from first listing (2017-08/11) to
2020-12-31. Spot, not perpetual: no funding history exists before 2019 for most of the span, so funding is set to 0
(stated limitation; perpetual longs usually *paid* funding in bull phases, so this flatters long-only slightly).

## Rules (frozen from Round 2, no re-tuning)
SA rule: signal = sign of the 20-day return (long-only: max(0, sign)); size to 40% annual volatility (30-day), cap 2x;
daily (SA-L, SA-LS) or weekly (SA-L-W, SA-LS-W) rebalance; costs 0.10% per side (2x reported); minimum notional
BTC 50 / ETH 20 / BNB 5 USDT; 300 USDT account (`sim.py`).
Baskets: **primary BTC/ETH/BNB, one third each** (SOL did not exist; BNB was the third most liquid); secondary BTC/ETH halves.
Trade accounting fixed: a sign flip closes a trade (the Round 2 long/short PF figures were wrong for that reason).

## Baseline
Random-timing twin per basket: same exposure fraction and holding lengths, entry days drawn at random (long-only),
or random direction per holding period (long/short); 200 replicas; percentile of final equity.

## Bars (primary basket, 2017-08 → 2020-12)
🟢 PF ≥ 1.10, PF at 2x costs ≥ 1.05, max DD ≤ 50%, both halves positive (2017-08→2018-12 including the crash;
2019-2020), random twin ≥ p95. 🟡 positive overall with PF ≥ 1.10 and twin ≥ p90. 🟠 positive overall. 🔴 otherwise.
A 🟢 here plus the 2021-26 result makes it the first candidate for a paper forward test on 300 USDT.

---

## RESULT (2026-10-04): 🟢 all 8 variants on 2017-08 → 2020-12 (data never used by research)

| Basket · variant | 300 → | CAGR | Max DD | 2017-18 | 2019-20 | PF / 2x | Random twin |
|---|---|---|---|---|---|---|---|
| BTC/ETH/BNB · SA-L | 1,569 | +65% | 30% | +12% | +364% | 3.94 / 3.66 | p100 |
| BTC/ETH/BNB · SA-LS | 2,177 | +82% | 29% | +57% | +357% | 2.38 / 2.23 | p100 |
| BTC/ETH/BNB · SA-L-W | 1,383 | +59% | 32% | +26% | +264% | 4.43 / 4.39 | p98 |
| BTC/ETH/BNB · SA-LS-W | 1,471 | +62% | 33% | +82% | +168% | 2.20 / 2.15 | p100 |
| BTC/ETH · SA-L / SA-LS / SA-L-W / SA-LS-W | 2,087 / 3,252 / 1,661 / 2,020 | +79 / +105 / +68 / +78% | 31 / 28 / 38 / 49% | all positive | all positive | 2.37-5.07 | p99-100 |

Full continuous account 2017-08 → 2026-09 (spot to 2020, perpetual futures with real funding from 2021), nothing re-tuned:
**BTC/ETH/BNB · SA-L-W: 300 → 5,980 (2x costs 5,432), CAGR +39.2%, max DD 39%, 8/10 years positive** (2018 −4%, 2022 −29%).
With a hard 1x leverage cap (live setting): 300 → 5,732, CAGR +38.6%, max DD 38%. Gross exposure median 46%, > 100% on 4.2% of days.
Positions at 300 USDT: median 88 USDT; BTC below its 50 USDT minimum on 1% of days.

**Candidate for forward testing: `MAJORS-TREND` = SA-L-W on BTC/ETH/BNB, one third each, 1x cap.** Chosen among the passing
variants for the lowest full-span drawdown (tied with SA-L) and the fewest orders (weekly rebalance; ~6 trades/year/coin).
Caveats: pre-2021 used spot prices with zero funding; the 2021-26 part is development data for BTC/ETH (the rule was never tuned on them).
Next gate: G6 forward test before any live use.
