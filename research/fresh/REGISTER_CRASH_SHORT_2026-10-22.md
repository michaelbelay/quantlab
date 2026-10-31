# CrashShort - registered before the run (2026-10-22)

Michael 2026-10-22: "yes test the short after crash rule" - after NFI bought LUMIA and BTW into crashes; NFI never shorts
a falling coin (its shorts sell sharp rises and it has a guard against shorting a dump). Question: would one plain "short
what is crashing today" rule have earned on the coins NFI trades? It is the mirror of BreakoutDay (🔴, 0/30 months).

## Rule (fixed now, not tuned after the run) - exact mirror of BreakoutDay
- Coins: the same 220 (BreakoutDay config list), data user_data/data_nfi (1h). Short only, 1x, isolated futures.
- Enter short on the close of a 1h candle when ALL hold:
  1. close < the lowest low of the previous 24 candles (a new 24-hour low)
  2. volume > 2 x the average volume of the previous 24 candles
  3. close < close 24 candles ago by more than -3% (the coin is down on the day)
- Exits: stop 4% against the trade; trailing stop 3% behind the best price once the trade is +4%; any trade still open
  after 24 hours is closed at the market.
- Size: 50 USDT per trade, 6 slots, wallet large enough never to run out (measurement, as BreakoutDay run 2).
- Costs: the old bot's Binance futures fees and funding. Period 2024-04-01 .. 2026-09-30.

## Reported (report only, no re-tuning)
Total, per month, trades, win rate, average trade, exits, market-fit table (does it earn on down / weak-breadth days?).

## Known limits, stated before the run
- Same 30 months as the other tests; a first look, not an unseen-data test.
- quantlab's momentum/breakout families all failed on unseen data; this checks the short mirror on the live coins.

## Result (automatic, rule unchanged)
8869 trades, win 55.9%, avg -0.43%, -1929 USDT, months positive 5/30
