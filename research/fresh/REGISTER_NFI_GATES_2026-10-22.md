# NFI coin-level gates - registered before the run (2026-10-22)

Michael 2026-10-22: "ok do the backtest" - after LUMIA (bought 10:16 into a pump-and-dump, closed -11.26 USDT) and the
assessment of the "derivatives features" prompt. Question: would a coin-level check at the moment NFI opens a trade
have skipped the bad trades without skipping too many winners?

## Trades
- research/fresh/nfi_bt_full223/chain_1m.json - NFI X8 (live strategy file, unchanged), NFIFull coins, 2024-04 .. 2026-09,
  1,935 trades (1,447 long, 488 short). Result per trade = profit_ratio x 33.33 USDT (200 budget / 6 slots, no compounding).

## Data (all Binance, all public)
- Price/volume: user_data/data_nfi 1h futures candles (local).
- Funding: user_data/data_nfi 1h-funding_rate (local).
- Open interest, top-trader and taker ratios: data.binance.vision daily "metrics" files (5-minute rows), the trade's
  open day and the day before. Verified live 2026-10-22 (columns: sum_open_interest_value, count_toptrader_long_short_ratio,
  sum_toptrader_long_short_ratio, count_long_short_ratio, sum_taker_long_short_vol_ratio).
- Liquidations: no public history - not tested.
- Only data stamped before the trade's open time is used.

## Gates (thresholds fixed now, not tuned after the run)
- G1 pump-dump (longs): in the 24 h before entry the high was >= +15% above the close 24 h earlier AND the biggest 1 h
  volume in those 24 h was >= 10x the median hourly volume of the 6 days before. (LUMIA live: +19%, ~35x.)
- G2 OI spike (longs): highest open interest (USDT) in the 24 h before entry >= +30% above the open interest 24 h earlier.
  (LUMIA live: 5.95M -> 8.5M = +43%.)
- G3 crowded long (longs): funding z-score >= 2 (last settled rate vs the 90 settlements before) AND open interest +5%
  or more over 4 h AND price within +-2% over 4 h.
- G4 crowded short (shorts): funding z-score <= -2 AND open interest +5% or more over 4 h AND price 4 h change >= -2%.

## Report (report only, no re-tuning)
Per gate: trades fired / not fired, win rate, average %, USDT; net effect of skipping the fired trades; the same split
for 2024-04..2025-06 and 2025-07..2026-09; how many of the worst 24 trades (the losers among trades that went >= 7.7%
underwater) it would have skipped; data coverage.
A gate counts as useful only if skipping its trades adds USDT in BOTH halves.

## Known limits, stated before the run
- A skipped trade frees a slot that another trade might have used; ignored here (the effect is measured trade by trade).
- Same 30 months NFI was backtested on; a first look, not an unseen-data test.
- quantlab killed funding crowding (C40) and the opportunity engine's OI conditions as ENTRY signals; this tests them as
  filters on NFI's own trades, a different question.

## Result (2026-10-22, rules unchanged) - all four gates 🔴
Data coverage 1,935/1,935 trades. All trades: win 96.5%, +4,125 USDT at 33.33/trade.
| gate | fired | win | avg | USDT of fired trades | skipping adds | halves | worst-24 losers skipped |
|---|---|---|---|---|---|---|---|
| G1 pump-dump | 318 | 97.8% | +6.32% | +670 | -670 | -116 / -554 | 5 |
| G2 OI spike | 336 | 97.6% | +5.96% | +668 | -668 | -114 / -553 | 5 |
| G3 crowded long | 2 | 100% | +7.95% | +5 | -5 | 0 / -5 | 0 |
| G4 crowded short | 1 | 100% | +16.1% | +5 | -5 | -5 / 0 | 0 |
Diagnostic (report only): the 24 worst losers (-168 USDT total) look like ordinary trades at entry - median pump 7.9%,
OI rise 6%, funding z -0.1, same as the trades that recovered. Buying after a pump is among NFI's BEST trades on these
coins; LUMIA was the unlucky minority. Only the account long/short ratio was a bit higher for the worst (1.75 vs 1.37) -
noted, not tested (would be a new, unregistered rule).
