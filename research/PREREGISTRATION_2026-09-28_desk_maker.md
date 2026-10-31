# Pre-registration: 15m / 30m breakout-with-flow with LIMIT (maker) entries

**Drafted 2026-09-28, before any limit-order test has been run. Status: APPROVED by Michael on 2026-09-28 ("approved"), unchanged from the draft he reviewed. LOCKED.**
Once approved this document is LOCKED; a wrong rule is fixed by a new, dated pre-registration.

## 1. The question

At 15m/30m the breakout-with-flow setup had real gross edge (30m: about +0.14 R per trade) and market-order costs (about 0.15 R) ate all of it (`DESK15M_REPORT.md`). A limit order pays the **maker** fee (0.02%) with no slippage instead of 0.05% + 0.02%. But a limit order only fills if price comes back, and the breakouts that never come back are probably the best ones.

**After both effects (lower cost, worse selection), can a person scalping by hand with limit entries make money on 15m/30m breakouts, on coins and months never tuned on?**

## 2. What I have and have not seen

- **Seen:** 15m/30m results for this setup with market entries on **dev coins x dev period**, including the zero-cost diagnostic, and today's 1h/4h results. A pass on dev x dev is partly expected and weak on its own.
- **Not seen:** any 1-minute data (downloaded 2026-09-28, used only for this test), and any limit-order result.
- **The sealed quadrant (holdout coins x 2026-03-26..2026-09-25) has never been opened.** This test is the one reserved to use it (agreed 2026-09-28). The short-1h idea is tracked on future data instead (`PREREGISTRATION_2026-09-28_short1h_forward.md`).

## 3. Data (fixed)

Same 30 coins, same window (2024-09-01 .. 2026-09-25), same splits as the earlier desk tests. Signals from the existing 15m bars (30m resampled). **Fills and exits walked on 1-minute bars** (`klines_1m.parquet`, Binance archive). Order-flow features exactly as in `desk15m_run.py`.

## 4. Splits (fixed — identical)

Dev coins: BTC, ZEC, XRP, NEAR, WLD, DOGE, UNI, LINK, ADA, AVAX, ONDO, BNB, ARB, BCH, DOT.
Holdout coins: ETH, SOL, ENA, SUI, RARE, TAO, FIL, LTC, 1000PEPE, QNT, DASH, ARK, AAVE, SAGA, FET.
Dev period 2024-09-01..2026-03-25; sealed period 2026-03-26..2026-09-25. Development on dev x dev only; holdout x sealed opened once at Stage 4.

## 5. How a trade is simulated

**Signal:** breakout with flow, identical to the 15m/30m definition — long: close above the highest high of the previous *N* bars, volume >= *k* x 20-bar average, taker-buy share >= 55%, open interest up over the last hour (short is the mirror).

**Entry — a resting limit order:**
- Placed **1 minute after the signal bar closes** (a person reading the card and typing the order).
- Price, one of two fixed rules (*E*):
  - `retest`: at the breakout level itself — the previous *N*-bar high for a long (low for a short).
  - `pullback`: signal close minus 0.25 x ATR(14) for a long (plus, for a short).
- **Fills only if price trades THROUGH the limit** on a 1-minute bar (long: 1m low strictly below the limit). A touch is not a fill — at the touch you are usually at the back of the queue. Fill price = the limit (or the 1m open if it gaps through, which is better).
- **Cancelled if unfilled after 2 signal bars** (30 min on 15m, 1 h on 30m) — the card expiry rule.
- A signal that doesn't fill is a **missed trade**: it scores nothing, and the fill rate is reported.

**Exits (placed as a bracket on fill):**
- **Stop:** *s* x ATR(14) of the signal timeframe from the fill price; a stop-market order — **taker fee + slippage**.
- **Target:** *r* x the stop distance; a resting limit — **maker fee, no slippage**, filled only when price trades through it.
- **Time stop:** 16 signal bars after the fill; market exit — taker + slippage.
- Walked on 1m bars. If a 1m bar reaches both, **stop first**. In the fill bar itself only the stop is checked (a fill and a target in the same minute is not counted).

**Costs:**
| | Base | 2x |
|---|---|---|
| Maker fee (entry, target) | 0.02% | 0.04% |
| Taker fee (stop, time stop) | 0.05% | 0.10% |
| Slippage (taker exits only) | 0.02% | 0.04% |

Plus real funding for every settlement held through. One open trade or live order per coin per combination; no portfolio cap; unit **R**.

## 6. Grid (fixed)

| Parameter | Values |
|---|---|
| *N* | {20, 48} |
| *k* | {1.5, 2.5} |
| entry rule *E* | {retest, pullback} |
| stop *s* | {1.0, 1.5} x ATR |
| target *r* | {1.5, 2.0} x stop |
| direction | long, short (separate candidates) |
| timeframe | 15m, 30m |

**128 combinations exactly.** Nothing added after results are seen.

**Reported for every combination, not gated:** fill rate, and "missed winners" — what the market-entry version made on the signals the limit order missed (the price of adverse selection).

## 7. Gates (same structure as the earlier desk tests)

### Stage 1: dev coins x dev period
1. >= 150 **filled** trades, on at least 10 of 15 coins.
2. PF >= 1.15 at base costs.
3. PF >= 1.05 at 2x costs.
4. Positive expectancy on at least 9 of 15 coins.
5. Beats random: random signal times with the **same limit-order mechanics** (placement, fill-through, expiry, exits, costs), 200 runs, matched filled-trade count; expectancy above the 95th percentile. This tests whether the signal adds anything beyond "buy dips with a limit".

### Stage 2: walk-forward (dev coins, dev period)
Train 6 months / test 2 / step 2 → 6 folds (2025-03..2026-03). Per direction x timeframe, pick the highest training PF with >= 30 filled trades and PF >= 1.10; none qualifying → fold scores 0. **Pass: OOS R > 0 and >= 4 of 6 folds positive.**

### Stage 3: robustness (dev x dev)
6. Each parameter's neighbour still PF > 1.0.
7. **Human delay:** order placed 15 minutes after the signal bar closes instead of 1 minute — still PF > 1.0.
8. Removing the single best coin leaves PF >= 1.10.

### Stage 4: sealed quadrant, ONCE, at most 5 combinations
9. >= 50 filled trades. 10. PF >= 1.10. 11. PF >= 1.00 at 2x costs.

## 8. Decision rule

**Validated only if all 11 gates pass.** Everything else is rejected. No partial credit, no loosened re-runs. If nothing passes, the panel stays empty.

## 9. If it validates

A card shows: limit price, stop, target, and expiry (2 bars). The operator places it as a limit order with TP/SL attached on Binance. Every card graded automatically; demotion after 100 graded cards below 0 R.

## 10. What I expect (written before running)

- Maker entry plus maker targets cut costs to roughly **0.05-0.08 R per trade** (stops and time exits still pay taker) — about half of before.
- **The open question is adverse selection:** fills come from breakouts that fail back to the level, which are the weaker ones. If that costs more than ~0.07 R per filled trade, the saving is gone.
- **Most likely result: nothing passes**, most likely at G2/G3 or at walk-forward, with `retest` filling more often but selecting worse than `pullback`. 30m has a better chance than 15m.

## 11. Outputs

- `research/desk_maker_run.py` — one seeded run (seed 20260929), this file's SHA-256 in every output.
- `research/results/desk_maker_stage1.json` … `_stage4.json`.
- `research/DESK_MAKER_REPORT.md`.
- Only if something validates: `user_data/desk/setups.json`.
