# Trend ensemble from outside research - registered before the run (2026-10-25)

Michael 2026-10-25: "that pond is drained" - search outside, keep going until there is a solution. Source:
Zarattini, Pagani, Barbon, "Catching Crypto Trends; A Tactical Approach for Bitcoin and Altcoins" (SSRN 5209907,
SFI 25-80). Reported: top-20 rotation net Sharpe > 1.5, CAGR ~18%, max drawdown ~11% (secondary summary).

## Rules as published (from the CXO / Concretum summaries; full PDF not reachable)
- Daily closes. Lookbacks N in {5, 10, 20, 30, 60, 90, 150, 250, 360} days.
- Entry for lookback N: close > highest close of the previous N days.
- Trailing stop: stop = max(previous stop, (highest close N + lowest close N) / 2); exit when close < stop.
- Each coin's weight = average over the 9 lookbacks of (1 if in position else 0) x 25% / (annualised 90-day stdev of
  daily returns). Total exposure capped at 200% of equity (scaled down pro rata). Rebalanced daily at the close.
- Universe: monthly, the 20 most liquid coins by median 30-day quote volume, coins listed >= 365 days. Coins leaving
  the universe are closed.
- Costs: 0.10% of traded notional (fee + slippage). Funding not counted (stated limit).

## Variants (fixed now, no others)
- A1 long-only exactly as above (the paper).
- A2 long + short mirror: also short for lookback N when close < lowest close of N days, stop = min(prev stop,
  midpoint), exit when close > stop. Net weight per coin = average of (+1 long / -1 short / 0) x vol scale.
- A3 A1 on BTC + ETH only (no rotation; the paper's single-asset case extended to ETH).

## Data
- Binance USDT-M daily candles 2020-01 .. 2026-10-24, the NFIFull 220 coins (coins traded now, no dead coins).
  Trading starts 2021-01-01 (360-day warm-up). Equity 300 USDT, results also in %.

## Pass rule (fixed now), for a 🟡 paper forward test
- Total return > 0 AND max drawdown <= 20% AND >= 4 of 6 calendar years 2021..2026 positive AND 2022 >= -5%
  AND last 12 months (2025-10-24 .. 2026-10-24) > 0. Otherwise 🔴.
- Report for Michael's rule (2026-10-25): longest losing stretch of the account (days under its last high), per-position
  stats (lookback trades: average hold, % ending red, average win / loss in USDT at 300 equity).

## Known limits
- The 220 list is today's coins (survivorship towards survivors; the paper used a bias-free set). Rules come from
  summaries, not the PDF; any difference from the paper is stated in the result.

## Result as registered (automatic, 2026-10-25) - all 🔴
- A1 300 -> 470, max DD -95%, 2022 -71%, 2025 -57%. A2 300 -> 112, DD -98%. A3 BTC+ETH 300 -> 777, DD -29%, last 12 m -7.6%.
- Cause (my registration, not the paper): I gave EACH coin 25% vol and capped the total at 200%, so the book ran
  near 2x in altcoins. The paper's portfolio is an equal-weight average of single-coin strategies (each 25% vol), which
  is why it reports ~11% drawdown.

## Correction registered BEFORE re-running (2026-10-25) - B variants, nothing else changed
- B1 = A1 with coin weight divided by the number of coins in the universe that day (20 here; 2 for B3).
- B2 = A2 with the same division. B3 = A3 with division by 2.
- Same pass rule. If these pass, the paper's sizing is the reason, and the result is still checked on paper forward.

## B result (2026-10-25)
- B1 long-only: 300 -> 446, DD -14%, 2022 -5.4% (fails the -5% line), 🔴.
- B2 long+short: 300 -> 398, DD -14.5%, years 2021 +20.9 / 2022 +5.9 / 2023 +1.5 / 2024 +5.9 / 2025 -6.6 / 2026 +3.2, last 12 m +4.9%, Sharpe 0.51 -> 🟡 by the rule, BUT average exposure is only 13% of equity: wins average +0.10 USDT, 5% a year. Not useful at this size.
- B3 BTC+ETH: 300 -> 504, DD -15%, last 12 m -3.7% -> 🔴.
