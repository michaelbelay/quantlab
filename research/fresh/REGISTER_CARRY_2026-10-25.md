# Funding carry (spot long + perp short, market-neutral) - registered before the run (2026-10-25)

Outside research: market-neutral was the only professional group with gains in 2025 (+14%) and 2026 (+2.15% YTD);
funding carry is the most documented retail-sized version (3-8% a year in bear phases, 10-40% in bull phases).
quantlab F1/F6/C08 used funding as a DIRECTION signal; pure hedged carry was never tested here.

## Rules (fixed now)
- Every Monday 00:00 UTC rank the NFIFull coins that have funding data by their average funding over the last 7 days.
  Hold the top 5 whose average is >= +0.01% per 8 h; empty slots stay in cash.
- Each held coin: long spot + short perp of equal size; the price moves cancel, the profit is the funding received
  over the next 7 days (actual rates, negative rates are paid).
- Capital 300: 200 USDT spot + 100 USDT perp margin (2x), so 40 USDT notional per coin.
- Costs: 0.30% of notional when a coin enters and 0.30% when it leaves (spot 0.10% + perp 0.05% each way, plus
  slippage). A coin kept the next week pays nothing.
- Squeeze risk: if a coin's 1h high in the week is >= +40% above the Monday price, the 2x perp leg is counted as
  liquidated: loss = its 20 USDT margin minus the spot leg's gain at +40%, then the coin is out.
- Period 2022-02-07 .. 2026-09-28 (funding data 2022-01 .. 2026-09). Limits: spot availability and the spot-perp
  basis are not modelled; every NFIFull coin is assumed to have a spot market.

## Pass rule (fixed now), for a 🟡 paper forward test
- >= +10% a year on 300 on average, every calendar year 2022..2026 positive, account max drawdown <= 5%. Else 🔴.

## Result as registered (2026-10-25) - 🔴
- -346 USDT, 103 "squeezes": the coins with the highest funding often jump +40% in a week, and at 2x that kills the
  perp leg. Report-only check at 1x showed two fake +267 weeks: a price that jumps ~10x in the data (token
  redenomination), which the squeeze line turned into a gain. Without those, 1x carry made about +69 USDT in 4.6 years.
- 52 of the 220 coins have no Binance spot market, so the spot leg could not even be bought.

## C2 registered BEFORE running (2026-10-25), nothing else changed
- 1x hedge: 150 USDT spot + 150 USDT perp margin, 30 USDT notional per coin, 5 coins. Squeeze line at +90%
  (1x short liquidation ~+100%): loss = 30 margin - spot gain at +90% (= -3 USDT) - costs.
- Only coins with a Binance USDT spot market today (research/fresh/carry/spot_usdt.json, 168 of 220).
- A coin whose week high is >= 3x its Monday price is a data error: skipped that week, no profit, no loss.
- Same pass rule (>= +10%/year, every year positive, DD <= 5%).

## C2 result (2026-10-25) - 🔴
-28.5 USDT over 4.6 years (2022 -3.3, 2023 -5.5, 2024 +6.2, 2025 -13.0, 2026 -12.9), DD -10%, avg 1.6 coins held. On coins you can actually hedge with spot, carry does not pay after costs.
