# Scalping families on 5m candles - registered before the run (2026-10-29)

Michael 2026-10-29: Tokyo server question -> "ok test ... be in urgent please". Test scalping BEFORE buying a server.
Live FlowTrend is left alone.

## Coins (fixed now)
FlowTrend's 20-coin live list (research/fresh/strat_bt/FlowTrend/config.json). Nothing else.

## Data / period (fixed now)
5m futures candles user_data/data_nfi, 2024-02-01 .. 2026-09-30 (first 2 days per coin = indicator warm-up).

## Families (fixed now) - signal on a 5m close, entry at the NEXT bar's open, long and short mirrored
ATR = 14-bar ATR on 5m. Exits checked on bar high/low; stop and target in the same bar = stop (conservative).
- S1 Bollinger fade: close outside BB(20, 2.5) AND RSI(3) < 5 (long) / > 95 (short). Target = BB middle at signal,
  stop 1.5 ATR, max 12 bars (1h).
- S2 Trend pullback: EMA(600) (= ~50h) rising over 12 bars and close > EMA(600) AND RSI(2) < 10 -> long
  (mirror for short). Target 1 ATR, stop 1.5 ATR, max 24 bars (2h).
- S3 Volume breakout: close > highest high of prior 12 bars AND volume > 3 x mean volume of prior 288 bars -> long
  (mirror). Target 1.5 ATR, stop 1 ATR, max 12 bars.
- S4 Spike fade: bar range > 4 x ATR(prior bar) AND volume > 5 x mean of prior 288 -> fade the bar's direction
  (red bar -> long). Target 1 ATR, stop 1 ATR, max 6 bars (30m).
- S5 Daily VWAP fade: deviation of close from rolling 288-bar VWAP > 3 ATR -> fade, target = VWAP at signal,
  stop 1.5 ATR, max 24 bars.

## Account (fixed now)
300 USDT, 6 slots, stake = equity / 6 at entry, 1x, one open trade per coin at a time, no new signal on a coin
while it has a trade. Fees: taker 0.05% per side (main result). Signals at the same bar: earlier coin order.

## Report (no re-tuning after the run)
Per family: trades, avg % per trade (net), win %, avg win / avg loss USDT, trades >= +10 USDT, worst trade, final
equity, max drawdown, by year, long vs short. Report-only extra: same trades with 0.02% per side (maker / limit
orders), to show how much the fee level matters - not a separate result.
