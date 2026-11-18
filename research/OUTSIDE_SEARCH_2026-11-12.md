# Outside search for bear and scalp ideas, 2026-11-12

Michael 2026-11-12: search outside for bearish and scalp strategies, beyond what the project already did.

Method: first listed what the lab has already tested (so nothing killed comes back), then read published research
and venue documentation. **No price data was looked at for any candidate below** - nothing here is a result.
Each candidate is one counted trial once it is registered. The only numbers measured today are funding rates read
from Binance's public history (section 4).

## 1. What the lab's own records already settle

| question | what the records say | source in this repo |
|---|---|---|
| Do candle-pattern scalps have an edge before fees? | No. The five 5m families (477,268 trades) average -0.084 .. -0.116% at 0.05% per side and -0.024 .. -0.056% at 0.02% per side. Adding the fee back gives a gross edge of +0.016, +0.007, -0.016, -0.002, -0.003% per trade: zero. | research/fresh/scalp/result.json |
| Does a cheaper fee (maker) rescue them? | No. Zero gross edge stays zero at any fee, and limit entries add adverse selection: the breakouts that fill are the ones that fail (PF 0.78-0.99 in all 8 groups). | research/DESK_MAKER_REPORT.md |
| Do shorts on majors pay on bear days? | No. After a bear day the 19 coins rose on average over the next 1-7 days in both halves; shorts earned only in crash months (2022-05, 2022-11, 2025-03, 2025-11). | research/bear/SUMMARY_BEAR_SEARCH_2026-11-01.md |
| What did pay? | Being paid to be short: positive funding on a coin in its own deep bear (cdeep family). It fails the frequency rule (~14 entry days a year on 19 coins). | research/CONSISTENCY_RULE_2026-11-11.md |
| Already tested and failed (do not repeat) | hour of day, weekend, CME gap, turn of month, MAX / idiosyncratic vol / skewness / abnormal volume, pairs, spot+perp carry, listing fade, BTC-leads-alts, Coinbase premium, crowd impulse, DVOL, OI positioning, liquidation flush, seconds lead-lag | FAMILIES*.md, research/fresh/REGISTER_*.md |

Reading: the lab has searched "which price pattern" about 8,700 times. What it has not searched is (a) dated public
events on small coins, (b) the price of the same contract on two venues, (c) contracts that are not crypto.
The four candidates below are those three gaps.

## 2. Candidate A - token unlock short, hedged with ETH (bear, frequent)

Evidence: Keyrock, 16,000+ unlock events: 90% of unlocks put negative pressure on price; the drift starts about 30
days before and steepens in the final week; team unlocks are the worst group, ecosystem unlocks slightly positive;
prices stabilise about 14 days after. Prices were measured against ETH, i.e. the effect is already a hedged one.

Not the same as the lab's `unlock_coin_rally_fade` (6 hand-picked majors, no unlock dates, a rally trigger).
This is an event study on the calendar itself, on every coin with a perp.

Draft to register (one version, nothing tuned):
- Event: cliff unlock of >= 1% of circulating supply whose recipients are team or investors. Date and size from an
  unlock calendar with history. **Open point: which source is free and has past schedules as they were known
  then (Tokenomist, DefiLlama emissions). Not checked. Without point-in-time dates there is no test.**
- Trade: 7 days before the unlock, 00:00 UTC, short the coin's USDT-M perp and long the same notional of ETHUSDT.
  Exit both at the unlock hour. Stop: the pair 15% against. Coin needs >= 10M USDT 24h volume.
- Costs: 0.40% round trip (two legs) + real funding on both legs. Funding matters: a crowded pre-unlock short pays.
- Gates: RULES_BEAR step 1 unchanged, plus the consistency rule (>= 3 trades a week is plausible: unlocks are weekly).

Why it may fail: published and widely known; the author is a market maker; the sample ends before this bear.

## 3. Candidate B - Binance "Monitoring Tag" short (bear, extends the one event edge the lab has)

The delisting short is the lab's only event idea on paper (136 events, +2.17% average, median +0.05%).
Binance puts coins on a Monitoring Tag before many delistings; coverage reports double-digit falls right after
(BIFI, FIS, KMD, MDT on 2025-06-05), but I found no study with numbers - the evidence is anecdotal.
Same announcement feed the delist bot already reads, different catalog entry, so the build is small.

Draft: same trade as delist D2 (short at the close of the first full 1h candle after the announcement, 72h,
+15% stop, 0.30% costs), event = "Binance Will Extend the Monitoring Tag to Include ...". One screen.

## 4. Candidate C - same coin, two venues: funding spread (market-neutral, any market)

Evidence: BitMEX Q2 2026 derivatives report: Hyperliquid funding averaged about 14.6% a year on BTC against about
7.4% on Binance (2023-2026), a gap of about 7.2 points (ETH 5.3), one-sided in 95% (BTC) and 89% (ETH) of rolling
90-day windows. Trade: short where funding is higher, long where it is lower; no price exposure.

Measured today on Binance (last 500 funding prints to 2026-11-12, via the UI's own API):

| contract | funding, % a year | share of prints > 0 | days covered |
|---|---|---|---|
| BTCUSDT | 5.6 | 92% | 166 |
| ETHUSDT | 3.8 | 83% | 166 |
| XAUUSDT (gold) | 8.3 | 55% | 83 |
| XAGUSDT (silver) | 7.5 | 50% | 83 |

So even in this bear a BTC short on Binance has been paid about 5.6% a year, and funding was positive 92% of the time.

Honest size: about 7% a year on the notional, before about 0.2% of entry/exit costs, with margin needed on both
venues. On the 300 USDT account that is roughly 10-20 USDT a year. It is the most regular return on this page and
it is too small to matter at this size; it only becomes interesting with the larger accounts.
Risks: one leg liquidated in a fast move while the other cannot be topped up in time; the gap can flip (it did
briefly in early 2025); a second venue with its own custody risk.
Test without money: log both funding rates hourly for 30 days and book the spread net of costs. No key needed.

## 5. Candidate D - the trend rule on contracts that are not crypto (diversifier, fails the frequency rule)

Binance USDT-M now lists gold, silver, platinum, palladium (since January 2026), ten US stock perps (May and
October 2026) and USD/BRL. Gold and silver are liquid (about 1.6 and 0.6 billion USDT a day); the stock perps are not
(0-95 million). Availability for a Swedish account is not confirmed - check that XAUUSDT opens in your account.

Evidence: Hurst, Ooi, Pedersen, "A Century of Evidence on Trend-Following Investing" (1880-2016, 67 markets):
positive in 8 of the 10 largest stock/bond drawdowns, average Sharpe about 0.4 per market, weakest in very fast crashes.

Draft: the MajorsTrend rule exactly as it is, long and short, on gold and silver daily history (decades of free
data), then paper on XAUUSDT / XAGUSDT. One run, no tuning.
Limits: 2-4 markets trade a few times a year, so this fails the consistency rule like MajorsTrend does. Gold is
-11% and silver -23% over the last 90 days: "not crypto" does not mean "going up".

## 6. Scalps - nothing to add, and why

No published short-horizon edge survives at candle level after costs, and the lab's own number (gross edge zero on
477,268 trades) agrees. The effects that are documented at seconds-to-minutes live in the order book and need
exchange-side latency; batch L already tested that route. Example of a published pattern that looks like a scalp:
Quantpedia's Bitcoin hours (buy 21:00, sell 23:00 UTC, 40.6% a year 2015-2023) - the article states no fees, and a
daily round trip at 0.10% costs 36.5% a year; the lab's S1 hour-of-day test already failed.

One cost fact worth checking on your own fee page: a September 2026 fee guide lists Binance USDC-margined perps at
0.00% maker / 0.04% taker against 0.02% / 0.05% for USDT-margined, and 10% off with BNB. If your account shows the
same, the trader's BTC/ETH/SOL trades are a fifth cheaper on the USDC contracts. It does not make any scalp pass.

## 7. Order I would run them in

1. B (monitoring tag): smallest build, reuses the delist reader, one screen.
2. A (unlocks): best fit to "earns in a bear and trades every week", but only once a point-in-time calendar is found.
3. C (venue funding): 30-day paper log; decide by account size, not by statistics.
4. D (metals trend): one run on free history; a diversifier, not the consistent strategy.

## Sources
- Keyrock, From Locked to Liquidity: https://keyrock.com/from-locked-to-liquidity-what-16000-token-unlocks-teach-us/
- BitMEX, Q2 2026 Derivatives Report: https://www.bitmex.com/blog/2026q2-derivatives-report
- OneKey, Hyperliquid vs Binance funding arbitrage: https://onekey.so/blog/ecosystem/hyperliquid-binance-funding-arbitrage-20260429/
- 1Token, TradFi Perpetual Arbitrage: https://blog.1token.tech/tradfi-perpetual-arbitrage/
- Stablecoin Insider, Binance TradFi perpetual contracts: https://stablecoininsider.org/binance-tradfi-perpetual-contracts/
- Hurst, Ooi, Pedersen, A Century of Evidence on Trend-Following Investing: https://fairmodel.econ.yale.edu/ec439/hurst.pdf
- Quantpedia, The Seasonality of Bitcoin: https://quantpedia.com/the-seasonality-of-bitcoin/
- Bitsgap, Binance trading fees (2026-09-10): https://bitsgap.com/blog/binance-trading-fees-explained-what-it-costs
- Monitoring Tag coverage (2025-06-05): https://www.itiger.com/news/2541807819
