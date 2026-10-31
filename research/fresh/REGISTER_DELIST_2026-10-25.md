# Delisting-announcement short - registered before the run (2026-10-25)

Michael 2026-10-25: keep searching; wins of 0.10 USDT are worthless - he wants trades with real size and a short
time in the red. Event idea from outside sources: when Binance announces it will delist a coin, holders must exit
and market makers leave; the price usually keeps sliding until the removal. Events are public and timestamped
(Binance announcement API, catalog "Delisting", 444 articles 2022-02-17 .. 2026-10-23).

## Events (fixed now)
- Every announcement titled "Binance Will Delist ..." (spot) or "Binance Futures Will Delist ..." (perps) that names
  coins; one event per coin, the first announcement wins. Coins without a USDT-M perp at that time are skipped.
- Excluded: "Binance Alpha", "Margin", "Notice of Removal of Spot Trading Pairs" (pair removals, not coins),
  stablecoins and leveraged tokens.

## Trade (fixed now)
- Short the USDT-M perp at the close of the first full 1h candle after the announcement time (so the first-minutes
  crash is NOT counted - only what a bot reading the announcement within the hour could get).
- Exit at the close 72 h later, or earlier at a +15% stop (1h high, checked first), or 3 h before the last candle
  of the perp's data if it is delisted sooner. Costs 0.30% round trip (thin books). Funding not counted.
- Size for the 300 account: 30 USDT notional per event, 2x isolated margin.
- Candles: fapi klines if the perp still trades, otherwise Binance's public archive data.binance.vision (monthly
  1h zips). Events without candles are counted and reported, not guessed.

## Pass rule (fixed now), for a 🟡 paper forward test
- >= 40 events traded, average net >= +2% per trade, median >= 0, positive in >= 3 of the years 2022..2026 that have
  >= 5 events, and average win >= 3 x 0.10 USDT is not the bar: average win must be >= 1 USDT at 30 USDT size.
  Otherwise 🔴. Report: hold hours, % red, worst trade, events by year.

## Result (automatic, 2026-10-25) - 🔴 (one line short)
135 traded (92 without candles), avg net +1.81% (bar 2%), median +0.49%, wins 53%, avg win +3.81 / loss -3.19 USDT
at 30 USDT, 39 stops, years 2022 +3.85 / 2023 -0.56 / 2024 +0.96 / 2025 +4.49 / 2026 +1.70 %. The coin had already
fallen -6.9% on average between the news and the 1h entry.

## D2 registered BEFORE running (2026-10-25), only the entry changes
- Entry at the close of the first full 5-minute candle after the announcement (a bot polling the announcement API
  every minute can do this). Same 72 h hold from entry, same +15% stop, costs, size and pass rule. 5m candles.
