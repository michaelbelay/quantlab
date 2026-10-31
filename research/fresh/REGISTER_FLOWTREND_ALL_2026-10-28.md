# FlowTrend on the full NFIFull list - registered before the run (2026-10-28)

Michael 2026-10-28: "try to see if we can put flowtrend fully on all the coins", like NFI Full (220 coins).
Live FlowTrend (20-coin list) is left alone.

## Coins (fixed now)
The 220 coins of user_data/live_profiles/NFIFull.json - the list the live NFIFull bot traded. Nothing else.

## Variants (fixed now) - only the "which coins may signal" filter changes
- FT-10: top 10 by last calendar month's traded value, ranked among all 220 (live rule, bigger pool)
- FT-30: top 30 the same way
- FT-ALL: every coin of the 220, no top filter
- Reference: FlowTrend as it runs live (20-coin list, top 10), same period and settings, re-run here
Everything else exactly as FlowTrend.py: z >= +2 / <= -2 on 24h taker-buy share vs 720h, 10-day trend, 24h cooldown,
stop 2 x daily move, exit 48h, 1x. Account: 300 USDT, 6 slots, stake = equity / free slots (live config), fees as
in the 10-21 FlowTrend backtest config.

## Period (fixed now)
2024-04-01 .. 2026-10-01 (same as the 10-21 FlowTrend backtest), 1h candles user_data/data_nfi, taker flow
user_data/flow_data (missing coins fetched from data.binance.vision, same script research/fresh/get_flow.py).

## Report (no re-tuning after the run)
Trades, avg % per trade, win %, avg win / avg loss in USDT, trades >= +10 USDT, worst trade, max drawdown,
final equity, months positive, longest losing streak.

## Result (automatic, 2026-10-28) - strat_bt/FlowTrendAll/result.json
| variant | trades | avg/trade | win | avg win / loss USDT | >=10 USDT | worst | final | max DD | 2024 / 2025 / 2026 |
|---|---|---|---|---|---|---|---|---|---|
| REF live (20 coins, top 10) | 829 | +0.61% | 47.9% | +4.47 / -3.34 | 44 | -18.3 | 634 | 21.0% | +94 / +183 / +57 |
| FT-10 (220, top 10) | 845 | +0.83% | 47.8% | +6.17 / -4.54 | 65 | -73.2 | 787 | 23.6% | +94 / +407 / -13 |
| FT-30 (220, top 30) | 1755 | +0.33% | 47.1% | +5.75 / -4.80 | 127 | -66.4 | 603 | 35.6% | +285 / +10 / +9 |
| FT-ALL (220, all) | 2643 | -0.07% | 46.9% | +3.53 / -3.22 | 67 | -32.2 | 145 | 77.3% | +231 / -159 / -226 |
Report-only: FT-10 best trade MYX long +222 (2025-09), worst RIVER short -73 / SIREN long -69 (no stop hit in 48h).
