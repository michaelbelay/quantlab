# VBreak4 Bull-Calm: protect open profit? — pre-registered 2026-10-11, before running

Michael (2026-10-11): the bot cuts losers at the stop but lets open profit float back; can we protect winners
without trimming them? Test it now on past data. Nothing live changes from this test.

## What is compared (5 exit designs, everything else identical to the live strategy)
Entries = VBreak4Both (volatility_breakout bars 4, atr_mult 2.0, btc_regime + volume, both directions), only trades
whose entry falls on a BTC Bull-Calm day (`vbreak_conditions.btc_conditions`, as the live gate). Engine
`research/engine` `simulate_pair`, fee 0.05% + slippage 0.05% per side + funding; 2x costs = pnl - 0.20 per 100.
ATR = ATR(14) of the signal bar (the same ATR that sizes the stop).
- **BASE**: as live: 2xATR stop fixed, no take-profit, opposite signal, 400 h.
- **BE2**: BASE + stop moves to the entry price once price has gone +2xATR in favour.
- **BE3**: same at +3xATR.
- **TR3**: from +3xATR: stop to entry, then trails 3xATR behind each hourly close (never loosens).
- **TR5**: same from +5xATR.
Nothing is closed early by these rules: they only move the stop. (Engine: tp_atr=(X,), tp_frac=(0,),
breakeven_after_tp1, trail_after_tp=1, trail_atr=3.)

## Coins and period
The 127 coins the live VBreak4 trades now (live profile whitelist minus its 6 blacklisted coins), development 1h
futures data, entries 2021-01-01 to data end. Today's list carries hindsight, equally for all five designs: this
test compares exits, it does not re-judge the strategy.

## Measures
Trades, PF, PF at 2x costs, net, win rate, 300 USDT book (`quant.book.replay`: 20 slots, <= 10 same direction,
stake equity/20, real minimum orders): final and max drawdown, years positive (book, per calendar year).

## Rule (4 alternatives = +4 trials)
A design is called BETTER than BASE only if: book final higher AND PF at 2x costs higher AND book max drawdown not
higher by more than 2 points AND higher net in at least 4 of the 6 years. If none is better: the live exits stay.
If one is: reported to Michael; any live change = a new strategy file, a new lock and his Start.
Runner `research/vbreak_exits.py` -> `research/VBREAK_EXITS_RESULT_2026-10-11.md/.json`.
