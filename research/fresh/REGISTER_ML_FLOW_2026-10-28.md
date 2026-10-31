# ML model on FlowTrend's coins - registered before the run (2026-10-28)

Michael 2026-10-28: "there are so many ways ... using AI models" - "go". LunarCrush (social sentiment) was the first
idea, but the free tier returns only the last 30 days, too short to test; so the AI idea #2: a machine-learning model
that learns from many inputs at once instead of one hand-made rule. Live FlowTrend is left alone.

## Coins (fixed now)
FlowTrend's 20-coin live list (research/fresh/strat_bt/FlowTrend/config.json). Only coins in that month's top 10 by
last calendar month's traded value may trade (same filter as FlowTrend).

## Inputs per coin, every 4 hours (00, 04, ... UTC, at the 1h close) - fixed now
flow z (24h taker-buy share vs 720h, as FlowTrend), flow z 6h, return 4h / 24h / 72h / 240h, return vs BTC 72h,
daily move (sd of 1h log returns 720h x sqrt24), volume 24h vs 30-day average, funding rate (last, and 3-day mean),
BTC return 24h / 240h, Fear & Greed index (yesterday's value, alternative.me), hour-of-day not used.

## Target and model (fixed now)
Target: return over the next 48 h > 0 (long view). Model: sklearn HistGradientBoostingClassifier, default settings
except max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=200, random_state=0.
Walk-forward: for each month 2024-04 .. 2026-09, train on ALL rows with a known 48h outcome before that month's
first day (from 2022-03), predict that month. No row is ever predicted by a model that saw it.

## Trades (fixed now)
- Long if P(up) >= 0.60; short if P(up) <= 0.40. One signal per coin and side per 24 h.
- Entry at the signal's 1h close, stop 2 x daily move from entry (checked on 1h high/low, stop first),
  exit 48 h after entry. 1x. Fees 0.05% per side (as the FlowTrend backtest), funding not counted.
- Account 300 USDT, 6 slots, stake = equity / 6 at entry (live FlowTrend setting). A signal is skipped if 6 are open.
- Signals at the same hour: highest confidence |P - 0.5| first.

## Report (no re-tuning after the run)
Trades, avg % per trade, win %, avg win / avg loss in USDT, trades >= +10 USDT, worst trade, final equity, max
drawdown, by year, longs vs shorts - next to FlowTrend's own result on the same coins and period (300 -> 634).

## Result (automatic, 2026-10-28) - ml_flow/result.json
1,845 trades, avg -0.01%/trade, wins 49.8%, avg win +1.95 / loss -2.02 USDT, 9 trades >= +10 USDT, worst -9.77,
300 -> 220.54, max drawdown -57.4%, years 2024 -48.7 / 2025 -63.5 / 2026 +32.8 USDT; longs -0.36%, shorts +0.31%.
FlowTrend on the same coins and period: 300 -> 634.
