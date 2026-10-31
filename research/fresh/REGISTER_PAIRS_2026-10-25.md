# Pairs trading (distance method, hourly) - registered before the run (2026-10-25)

Outside research: Binance pairs-trading studies (IEEE Access 2020, 26 coins: daily distance method -0.07%/month,
better at higher frequency; a 2022 study of 30 Binance coins: distance method profitable at 1m/5m/60m). Market-neutral:
a long and a short of equal size, so a bleeding market does not hurt by itself. Professionals' only winning group in
2025-26 was market-neutral (Hedgeweek, The Block).

## Rules (fixed now)
- Coins: the 30 most liquid of the NFIFull 220 by median 30-day quote volume, re-chosen at each formation.
- Formation: every Monday 00:00 UTC, last 30 days of 1h closes. Normalised price = close / first close of the window.
  Distance = sum of squared differences of normalised prices. Pick the 10 closest pairs, each coin in at most one pair.
- Trading (the following 7 days, 1h closes): spread = log(A) - log(B) - mean of that over the formation window;
  sd = its formation stdev. Open when |spread| > 2 sd: short the rich coin, long the cheap one, equal USDT each.
  Close when the spread crosses 0, or |spread| > 4 sd (stop), or at the end of the week. A pair can re-open in the week.
- Size: 300 USDT, 10 pairs, 15 USDT per leg (30 per pair, 1x). Costs 0.20% per leg round trip (0.40% per pair trade).
- Funding not counted (stated limit). Entry/exit at the 1h close that triggers.
- Period 2022-02-07 .. 2026-10-19 (user_data/data_nfi 1h; continuous data only).

## Pass rule (fixed now), for a 🟡 paper forward test
- Net USDT > 0, average net trade >= +0.30% of pair notional, >= 4 of 5 calendar years 2022..2026 positive,
  last 12 months > 0, max drawdown of the 300 account <= 20%. Otherwise 🔴.
- Report for Michael's rule: average hold hours, % of trades ending red, average win / loss USDT, longest trade.

## Result (automatic, 2026-10-25) - 🔴
19,686 trades, -1,206 USDT, avg -0.20%/trade, 28% wins, every year negative; 91% of trades hit the 4 sd stop (spreads keep widening out of sample). research/fresh/pairs/result.json
