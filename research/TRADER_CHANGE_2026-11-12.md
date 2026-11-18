# Trader change, 2026-11-12 (paper book and live safety)

Signal rule (trader/flowtrend.py) is NOT touched. What changed is how fills are booked and how the trader survives
downtime. Applies from the first trader start after this date; paper trades #1-#7 were opened under the old booking.

## Paper booking, old -> new

| | until 2026-11-12 | from now |
|---|---|---|
| entry / exit price | last price | last price moved 0.05% against us (settings.SLIPPAGE, same as the research) |
| funding | not booked | every funding stamp inside the holding time, rate x mark x amount (column `funding`, inside `pnl`) |
| stop | only if a 20 s price check saw it | also from the 1h candles' high / low, once per hour and at every start |
| exit after downtime | at the price when the trader came back | where and when the rule exited (candles); row gets a note |
| entry after a late start | up to 59 min after the candle close | only within 5 min of the close (settings.ENTRY_GRACE_S), else skipped |
| stop level | from the candle close, then re-derived for the record | one level, from the real fill, for record and order |

## Known wrong rows in the paper book (2026-11-03 reboot, 8 days down)

| # | coin | recorded | what the rule did (1h candles) |
|---|---|---|---|
| 4 | HYPE long | stop at 73.108 on 11-11, -11.37 | stop 81.716 never touched in its 48 h; time exit 11-03 14:00 at 86.304, about -1.46 |
| 5 | NEAR short | time exit at 3.715 on 11-11, +6.21 | time exit 11-04 13:00 at 4.004, about +1.46 |

Together the book shows -5.16 for the two; the rule made about 0.00. `python -m trader repair paper` prints the
exact figures from Binance candles, `--apply` writes them and keeps the old values in each row's note.

## New, both modes

- Day-loss switch: closed P&L of the UTC day + open trades at or below -6% of the wallet (settings.DAY_LOSS_HALT)
  -> no new entries until the next UTC day ("halted"); open trades are still managed; `resume` lifts it.
- Heartbeat and state files are written atomically; a damaged file reads as "unknown", not as an error.
- tools/watchdog.py + install_watchdog.bat: restarts paper trader / switcher / delist when they are not running.

## New, live only (still never run against the real account)

- Stop order refused -> tried twice -> position closed again at once; if that is refused too, the trade is recorded
  with a note and closed by the trader itself after 2 price checks beyond the stop ("stop_soft").
- A position on the account that is not in the trader's book (a manual trade, a lost record) is reported and that
  coin gets no new trade. The trader never touches such a position.
- A position that disappears away from its stop is recorded as "external", not as a stop.
