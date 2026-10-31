# Fact check: Binance Web3 "smart money" buy signals, 2026-10-07

Source: Binance Skills Hub `trading-signal` feed (public), all 158 signals it returns (BSC 58, Solana 100,
triggered 2026-09-30 .. 2026-10-07, all `buy`, 3-11 smart-money wallets each, median market cap $160k).
Prices: 5-minute candles from the `query-token-info` kline feed. Entry = open of the first candle after the
signal (median 2 minutes later, median price equal to the alert price). Cost assumed 1% round trip (DEX).
Raw data: `web3_baseline/` (`sm_uniq.json` signals, `sm_klines2.json` candles, `sm_outcomes.csv` per-signal results).

## Result: buying these signals lost money, badly and consistently

| Hold | n | Median | Mean | Trades up after 1% cost |
|---|---|---|---|---|
| 1h | 155 | −43% | −29% | 23% |
| 4h | 152 | −63% | −44% | 15% |
| 24h | 134 | −79% | −51% | 12% |

- The feed advertises "max gain since trigger": median **+88%**, mean +282%. That is the best price reached at
  any moment (median peak inside 24h: +35% from our entry). Typical path: short spike, then −87% low within 24h.
- Independent check with the feed's own numbers (current price vs alert price, signals ≥ 24h old): median
  **−93%**, only 6% above the alert price. Agrees with the candle-based result on 90% of signals.
- More wallets is not better: 5+ wallets 24h median −78%, win 6%; 3-4 wallets −79%, win 14%.
- Exit rules do not rescue it (walked on 5m candles, stop counted first): TP+20/SL−10 avg −6.4%, TP+30/SL−30
  −12.2%, TP+50/SL−25 −10.7%, TP+100/SL−50 −17.8%; real stops on thin tokens would fill worse.

## What it means
These signals mark the moment early wallets buy tiny new tokens; followers who buy after the signal are, on this
sample, mostly the exit liquidity. Fact for decisions: **do not follow these buy signals.**

Limits: one week, 158 signals, one market phase; shorting these tokens is not possible. The recorder
(`web3_recorder.py`) keeps every new signal so this is re-measured after 4 weeks
(`PREREGISTRATION_2026-10-07_web3.md`).
