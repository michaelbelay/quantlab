# BreakoutDay - registered before the run (2026-10-21)

Michael 2026-10-21: "yes test the breakout rule on the 220 coins". Today (2026-10-21) 164 of 220 coins rose, 19 by
more than 10%, and no live strategy bought: NFI and E0V1EN buy dips, none of the set buys strength on the day.

Question: would one plain "buy what is breaking out today" rule have earned on the coins NFI trades?

## Rule (fixed now, not tuned after the run)
- Coins: the NFIFull live list (220 coins, user_data/live_profiles/NFIFull.json); data user_data/data_nfi (1h).
- Timeframe 1h. Long only, 1x, isolated futures.
- Enter on the close of a 1h candle when ALL hold:
  1. close > the highest high of the previous 24 candles (a new 24-hour high)
  2. volume > 2 x the average volume of the previous 24 candles
  3. close > close 24 candles ago by more than +3% (the coin is up on the day)
- Exits: stop -4% from entry; trailing stop 3% under the best price once the trade is +4%; any trade still open after
  24 hours is closed at the market.
- Size: 300 USDT wallet, 6 slots, fixed 50 USDT per trade (no compounding), one trade per coin at a time.
- Costs: the old bot's Binance futures fees; market-style fills at the candle close.
- Period: 2024-04-01 .. 2026-09-30 (same as the NFI / E0V1EN / other strategy tests).

## Reported (report only, no re-tuning)
Total and per-month result, trades, win rate, average trade, worst drop, longest gap between trades, and the
market-fit table (does it earn on "up" / "strong breadth" days, where the live set is idle?).

## Known limits, stated before the run
- Same 30 months the other strategies were tested on; this is a first look, not an unseen-data test.
- quantlab tested many momentum / breakout families on unseen data and none survived; this run says whether this
  simple version earns on the live coins, nothing more.

## Result (2026-10-21, rule unchanged)
- Run 1, 300 USDT wallet: 300 -> 50 by 2024-07 (425 trades, -83%); stake 50 could no longer open. Kept in
  strat_bt/BreakoutDay/first_run_300.
- Run 2, same rule and 50 USDT stake, wallet large enough never to run out (measurement only):
  13,560 trades (14.9 a day), win 46.1%, average trade -1.01% (wins +2.24%, losses -3.79%), -6,810 USDT,
  **0 of 30 months positive** (best 2024-09 -66, worst 2025-11 -512).
  Exits: stop 6,557 · trailing 5,566 · 24 h 1,433.
- Market fit: negative in every market type; worst on strong-breadth days (-9.56 USDT/day) and up-trend days (-8.44).
- Verdict 🔴: buying a fresh 24 h high on volume loses on these coins; most breakouts fall back and hit the stop.
