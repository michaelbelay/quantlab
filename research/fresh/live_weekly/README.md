# Weekly live-vs-backtest check (built 2026-10-18, Michael: Friday 09:00)

Information only: never stops the bot, changes nothing, adds no gate. Michael decides.

## What it does
Every Friday 09:00 (local), task `Quantlab Weekly Live Check`, `weekly_check.py`:
1. **Is the machine working?** Backtests the live strategy file (`user_data/research_strategies`) with the live
   settings (`config_live_mainnet.json`: coins, 6 slots, 5m, limit orders) over the last 7 days, in its own data folder
   `user_data/data_weekly` (30-month data from `data_nfi` + recent candles from Binance public REST). Compared only
   from the moment the current live profile started (`live_lock.json` "taken"). Each backtest trade is matched with the
   live database (read-only): same coin, same side, opened within 15 min.
   - missed = backtest traded, live did not; explained by the bot log (paused / offline = no heartbeat > 5 min) or by
     live slots / the coin already being busy; otherwise **unexplained**.
   - extra = live traded, backtest did not.
   - fill gap = average (live − backtest) result on matched closed trades.
2. **Is the strategy still working?** Live closed trades since the profile started vs the 30-month NFI backtest
   (`research/fresh/nfi_bt_nfi48/chain_1m.json`, 692 trades 2024-04..2026-09): win rate, average trade, quiet gaps.

## Colours (fixed 2026-10-18)
- 🔴 bot not running at check time · ≥ 2 unexplained missed/extra trades · fill gap worse than −1.0% per trade
  (≥ 3 matched closed trades). → Windows notification.
- 🟡 1 unexplained trade · backtest trades missed because the bot was paused/offline/busy · no new trade for longer than
  the backtest's 90th-percentile gap (4.4 days) · with ≥ 10 closed live trades: win rate below the backtest's worst
  month (80%) or a negative average trade.
- 🟢 none of the above.

## Files
`latest.json` (UI Live tab card, /api/weekly), `history.jsonl` (one line per week), `report_<date>.md`, `work/` (backtest
config, log, export). First run 2026-10-17 evening: 🟡, the backtest's only trade since NFI46 went live (A/USDT long
10-17 17:10 UTC, +2.14%) was missed because the bot was paused 12:41–17:16 UTC. The 7-day backtest reproduced the paper
NFI bot's own trades of 10-14/10-15 (TIA, A, OP, CRV, WLD) at the same times.
