# Pre-registration: 15m / 30m manual signal research (decision desk)

**Drafted 2026-09-27, before any test has been run on the desk data. Status: APPROVED by Michael on 2026-09-27 ("approved, go ahead and run it"), unchanged from the draft he reviewed. LOCKED.**
Nothing in this document may be changed after the first test runs. If a rule turns out to be wrong, the fix is a new, dated pre-registration, and this one is reported as it was run.

## 1. The question

Is there any 15m or 30m setup, built from price indicators confirmed by order flow, that a person trading **by hand** on Binance USDT-M futures can take profitably **after taker costs**, on coins and months it was never tuned on?

A setup that passes becomes a card in the desk's Signals panel with the badge `validated`. Nothing else appears on the panel.

## 2. What I have and have not seen (contamination disclosure)

- **Desk data:** only download statistics (row counts, date range, missing days). No returns, no signal outcomes, no feature distributions.
- **Prior research on the same coins:** the 1h volatility-breakout work (2021-2026, 140-coin universe) overlaps with these coins and with this time window. It shaped my priors: breakouts work better than mean reversion, shorts have lost money on their own in every earlier test, 2025-26 is a choppy regime, high-churn strategies die at 2x costs. These priors shaped which setups are listed below. That is the only way they are used.
- **Live observation:** today's scanner and order-flow panel values for a handful of coins. That is one snapshot and is not used.

## 3. Data (fixed)

| Item | Value |
|---|---|
| Coins | 30 USDT-M perpetuals from `user_data/desk_data/universe.json` (top 30 by 24h quote volume, listed before 2024-09-01, stable/index contracts excluded) |
| Window | 2024-09-01 00:00 to 2026-09-25 23:45 UTC |
| Bars | 15m from the Binance archive. 30m is resampled from 15m (open of first, max high, min low, close of last, summed volume and taker-buy volume) |
| Order flow | taker-buy volume per bar (-> delta / CVD); 5-minute open interest, top-trader and global long/short ratios, taker long/short ratio; funding history |

**No lookahead.** Every feature is computed only from data available when the signal bar closes. The 5-minute metrics are **lagged one extra step (5 min)**, because Binance's publication delay for them is not documented. Funding is applied at its real timestamps and at the coin's real interval (8h for most coins, 4h for seven of them).

## 4. Splits (fixed by rule, before looking)

**Coins:** alternating 24h-volume rank from `universe.json`. Odd ranks go to dev, even ranks to holdout.

- **Dev (15):** BTC, ZEC, XRP, NEAR, WLD, DOGE, UNI, LINK, ADA, AVAX, ONDO, BNB, ARB, BCH, DOT
- **Holdout (15):** ETH, SOL, ENA, SUI, RARE, TAO, FIL, LTC, 1000PEPE, QNT, DASH, ARK, AAVE, SAGA, FET

**Time:**

- **Dev period:** 2024-09-01 to 2026-03-25 (about 19 months)
- **Sealed period:** 2026-03-26 to 2026-09-25 (the last 6 months)

This gives four quadrants. **Holdout coins x sealed period is never looked at during development and is opened once, at the end** (Stage 4). The other quadrants are dev coins x sealed period, holdout coins x dev period, and dev coins x dev period. Development uses only dev coins x dev period.

## 5. How a trade is simulated

- **Signal** on the close of bar *t*. **Entry at the open of bar t+1** as a market order: taker fee plus slippage, in the unfavourable direction.
- **Exits:**
  - a **stop** at *s* x ATR(14) from entry
  - a **target** at *r* x the stop distance
  - a **time stop** after *T* bars, exiting at the next bar's open
  - If a single bar touches both the stop and the target, **the stop is assumed hit first** (pessimistic).
- **Costs, base case:** taker fee **0.05% per side**, slippage **0.02% per side**, so **0.14% round trip**, plus real funding for any funding timestamp the trade is held through.
- **2x costs:** fees and slippage doubled, **0.28% round trip**.
- **One open trade per coin per setup.** A signal that fires while that setup already holds that coin is skipped. There's no portfolio cap: the operator chooses which cards to take, so every trade is scored on its own.
- **Result unit:** R, meaning profit or loss divided by the planned risk (the entry-to-stop distance). This makes coins and volatility levels comparable, and it's exactly what the desk's position calculator sizes.

## 6. Setups (fixed list: 5 families, each long and short, on 15m and 30m)

Each family has one indicator trigger and one order-flow confirmation. The order flow is the part that is new compared with earlier research.

| # | Family | Trigger (long; short is the mirror) | Order-flow confirmation | Parameters |
|---|---|---|---|---|
| B | **Breakout with flow** | close above the highest high of the last *N* bars | bar volume >= *k* x its 20-bar average, **and** aggressive-buy share of the bar >= 55%, **and** open interest up over the last hour | N in {20, 48}; k in {1.5, 2.5} |
| F | **Failed breakout / absorption** | the bar makes a new *N*-bar low but closes back inside the range | aggressive-sell share of the bar >= 55% (sellers pushed and were absorbed) | N in {20, 48} |
| P | **Pullback in trend** | 1h EMA50 > EMA200, and the bar's low touches the 15m/30m EMA20 and the bar closes above it | aggressive-buy share >= 52%, and open interest not down more than 1% over the last hour | EMA touch tolerance in {0.1%, 0.3%} |
| L | **Flush reversal** | a bar falling >= *m* x ATR with volume >= 3x its average | open interest **down** >= 1% over the last hour (forced closing, not new selling) | m in {2.0, 3.0} |
| X | **Crowding fade** | funding in the top 10% of the coin's own trailing 30 days **and** top-trader long/short ratio in its top 10% -> short (mirror for long) | price has made no new 20-bar high in the last 4 bars (the move is stalling) | decile threshold in {10%, 20%} |

**Exit grid, shared by all families:** stop *s* in {1.0, 1.5} x ATR; target *r* in {1.5, 2.0} x stop; time stop *T* = 16 bars (4h on 15m, 8h on 30m), fixed.

**Search budget:** 12 entry combos across the families (B 4, F 2, P 2, L 2, X 2) x 4 exit combos x 2 directions x 2 timeframes = **192 combinations exactly**. This is the whole search. No family, filter or parameter is added after results are seen.

Long and short are **separate candidates**. A family can pass on one side and fail on the other.

## 7. Gates

A combination has to pass every stage in order. Failing any single gate rejects it.

### Stage 1: dev coins x dev period, full sample

1. **At least 150 trades** in total, with trades on at least 10 of the 15 dev coins.
2. **Profit factor >= 1.15** at base costs.
3. **Profit factor >= 1.05 at 2x costs.** This is the gate that killed every high-churn strategy so far.
4. **Positive expectancy (R) on at least 9 of the 15 dev coins.**
5. **Beats random entry.** Run the same exits, costs, coins and trade count with random entry times, 200 times, which gives a distribution of random results. The candidate's expectancy must be above the 95th percentile of that distribution. This checks that the entry adds something beyond the exit geometry.

### Stage 2: walk-forward inside the dev period (dev coins only)

- **Folds:** train on 6 months, test on the next 2 months, then step forward 2 months. That gives 6 test folds covering 2025-03 to 2026-03.
- **Selection inside each fold:** within each family, direction and timeframe, choose the parameter combination with the highest training profit factor. Training must show **at least 30 trades and profit factor >= 1.10**. If nothing qualifies, that fold trades nothing and scores 0. (A missing profit-factor floor let a PF 0.918 pick through last time. This rule fixes that before it happens again.)
- **Pass criteria:** total out-of-sample R > 0 **and** at least 4 of the 6 folds positive, at base costs.

### Stage 3: robustness (dev coins x dev period)

6. **Parameter neighbours:** moving each parameter one step either way within the grid still gives profit factor > 1.0 at base costs.
7. **Human delay:** entering **one bar later** (the open of t+2, as if the operator took 15 or 30 minutes to act) still gives profit factor > 1.0 at base costs. A desk signal has to survive someone reacting late.
8. **Not one coin:** removing the single best coin still leaves profit factor >= 1.10.

### Stage 4: sealed quadrant (holdout coins x sealed period), run ONCE

Only for combinations that passed Stages 1-3, and **at most 5 of them**. If more than 5 survive, the 5 with the highest walk-forward out-of-sample R go forward and the rest are recorded as untested.

9. **At least 50 trades.**
10. **Profit factor >= 1.10** at base costs.
11. **Profit factor >= 1.00 at 2x costs.**

## 8. Decision rule

> **A combination is `validated`, and becomes a desk card, only if it passes all 11 gates across all four stages.**
> Every other result is **rejected** and never appears on the panel.

No partial credit, no "nearly", no re-running with loosened thresholds. If nothing passes, the Signals panel stays empty and the report says so plainly, with the numbers.

## 9. After validation (for the live scanner, stated now so it can't be bent later)

- Each card carries entry, stop, target and an **expiry of 2 bars**. After that the entry is stale.
- Every card is graded automatically, whether it was accepted or passed.
- **Demotion rule:** after **100 graded cards** from a setup, if the realised expectancy after base costs is below 0 R, the setup is removed from the panel.
- Frequency is reported but is not a gate. A setup that validates but fires less than about once a week across all 30 coins is shown anyway, with its rate.

## 10. What I expect (written before running)

At 15m and 30m, base costs of 0.14% round trip are roughly 20-35% of a typical 1 x ATR stop on these coins. Every high-frequency candidate in this project so far failed at 2x costs, and 2025-26 has been choppy. **The most likely result is that nothing passes.** The families with the best chance are probably L (flush reversal) and B (breakout with flow), because they trade rarely and only on large moves, where costs are a smaller share. This expectation is recorded so the result can be compared against it, not to lower any gate.

## 11. Outputs

- `research/desk15m_run.py`: one script, one seeded run (seed 20260927).
- `research/results/desk15m_stage1.json`, `_stage2.json`, `_stage3.json`, `_stage4.json`.
- `research/DESK15M_REPORT.md`: every combination with the gate it failed.
- Only if something validates: `user_data/desk/setups.json`, the exact rules that the live scanner will run.
