# Pre-registration: Binance Web3 boards as signals for Binance perps, 2026-10-07

Written before any recorded data existed (first snapshot 2026-10-07). Recorder: `web3_recorder.py` → `web3_feed.db`,
hourly via `scan.py --auto`.

## Question
When a coin that has a Binance USDT-M perpetual shows up on a Binance Web3 board (trending, smart-money inflow,
social hype), does its perp move differently from the market over the next 4h / 24h?

## Events (fixed)
- Boards: `trending` (top 20), `inflow` (top 10 by 24h net inflow), `hype` (top 10), `hype_pos` / `hype_neg`
  (hype top 10 split by sentiment Positive / Negative).
- A row counts only if its symbol matches an active Binance USDT-M perp **and** its reported market cap ≥ $100M
  (blocks same-ticker clone tokens; e.g. "SOL" on Base at $29M is not SOL).
- Event = first appearance of that coin on that board after ≥ 48h absent (cooldown per coin and board).
- Entry = open of the next 1h Binance perp candle after the snapshot.

## Outcome
- Perp return to +4h and +24h, **minus the median return of the top-200 USDT perps over the same window**
  (market-adjusted, so a market-wide move is not credited to the board).
- Day-weighted: events of one day are averaged first (same rule as the scanner).

## Decision (after ≥ 4 weeks AND ≥ 50 events on a board, not before)
- |day-avg market-adjusted return| > 0.20% (round-trip cost) **and** |day t| ≥ 2 → the sign gives the direction
  (LONG if positive, SHORT if negative) and the board becomes a scanner rule that starts 🟠 in the forward test.
- Otherwise: no edge, board dropped. 5 boards × 2 horizons = 10 tests; ~0.5 false hit expected at t ≥ 2,
  so a pass is only a forward-test candidate, never a trade on its own.

## Smart-money signals (on-chain tokens, not perps)
Baseline already measured on 2026-10-07 (`SMART_MONEY_RESULT_2026-10-07.md`): buying the signals lost a median
−63% after 4h. The recorder keeps every new signal; the same measurement is repeated after 4 weeks. Expectation
stated now: still negative. If the 4-week median 24h return after 1% cost is > 0 the claim is re-opened.
