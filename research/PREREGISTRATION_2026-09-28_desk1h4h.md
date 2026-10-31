# Pre-registration: 1h / 4h breakout-with-flow (decision desk)

**Drafted 2026-09-28, before any test at 1h or 4h has been run on the desk data. Status: APPROVED by Michael on 2026-09-28 ("both, start with 1" — option 1 being this test as drafted), unchanged from the draft he reviewed. LOCKED.**
Once approved this document is LOCKED. Nothing in it may change after the first test runs; a wrong rule is fixed by a new, dated pre-registration and this one is reported as it was run.

## 1. The question

The 15m/30m test (`PREREGISTRATION_2026-09-27_desk15m.md`, report `DESK15M_REPORT.md`) found nothing. A zero-cost diagnostic afterwards showed one setup with real gross edge — **30m breakout with flow, about +0.14 R per trade** — and taker costs of about 0.15 R per trade eating all of it.

Costs are fixed in price terms while stop distances grow with the timeframe (ATR at 1h is roughly 1.4x the 30m ATR, at 4h roughly 2.8x). So:

**Does the same breakout-with-flow setup, moved to 1h and 4h bars, keep enough edge per trade to survive taker costs, on coins and months it was never tuned on?**

A setup that passes becomes a `validated` card on the desk's Signals panel. Nothing else appears there.

## 2. What I have and have not seen (contamination disclosure)

This test is **more contaminated than the last one** and that must be said plainly:

- **Seen:** the 15m/30m results for this family on **dev coins x dev period**, including the zero-cost diagnostic. That result is the reason this test exists. Any pass on dev x dev is therefore partly expected and weak evidence on its own.
- **Seen:** the 2021-2026 1h volatility-breakout research on an overlapping coin universe (the vb_b4 work): breakouts carry edge, shorts lose standalone, 2025-26 is choppy, high-churn dies at 2x costs.
- **Not seen:** any 1h or 4h result on the desk data. **The sealed quadrant (holdout coins x 2026-03-26..2026-09-25) has never been opened by any test.** It is the only clean evidence available and is why Stage 4 decides.

## 3. Data (fixed — identical to the 15m/30m test)

| Item | Value |
|---|---|
| Coins | the same 30 USDT-M perpetuals, `user_data/desk_data/universe.json` |
| Window | 2024-09-01 00:00 to 2026-09-25 23:45 UTC (not extended — keeps the sealed quadrant identical) |
| Bars | 1h and 4h **resampled from the 15m archive**, aligned to UTC hours (4h bars start 00/04/08/12/16/20 UTC). Open of first, max high, min low, close of last, summed volume and taker-buy volume |
| Order flow | taker-buy volume per bar; 5-minute open interest (lagged one extra 5-min step, as before); funding history at real timestamps and intervals |

No lookahead: every feature uses only data available when the signal bar closes.

## 4. Splits (fixed — identical to the 15m/30m test)

- **Dev coins (15):** BTC, ZEC, XRP, NEAR, WLD, DOGE, UNI, LINK, ADA, AVAX, ONDO, BNB, ARB, BCH, DOT
- **Holdout coins (15):** ETH, SOL, ENA, SUI, RARE, TAO, FIL, LTC, 1000PEPE, QNT, DASH, ARK, AAVE, SAGA, FET
- **Dev period:** 2024-09-01 to 2026-03-25. **Sealed period:** 2026-03-26 to 2026-09-25.
- Development uses dev coins x dev period only. **Holdout coins x sealed period is opened once, at Stage 4.**

**Consequence stated in advance:** if anything reaches Stage 4, the sealed quadrant is spent for this family. A later breakout test on these coins would need new data (after 2026-09-25) as its holdout.

## 5. How a trade is simulated

- **Signal** on the close of 1h/4h bar *t*. **Entry at the open of the next 15m bar** (= open of bar t+1), market order, taker fee plus slippage in the unfavourable direction.
- **Exits:** stop at *s* x ATR(14) of the signal timeframe; target at *r* x stop distance; time stop after *T* bars of the signal timeframe, exiting at the next 15m open.
- **Exit path is walked on the 15m bars inside each 1h/4h bar**, so the stop/target order is resolved at 15m resolution. If a single 15m bar touches both, **the stop is assumed hit first** (pessimistic).
- **Costs, base:** 0.05% fee + 0.02% slippage per side = **0.14% round trip**, plus real funding for every funding timestamp held through. **2x costs:** 0.28% round trip. (Unchanged from the last test.)
- One open trade per coin per combination; no portfolio cap; result unit **R** (P&L / planned risk).

## 6. The setup (one family, fixed grid)

**B — breakout with flow**, exactly the 15m/30m definition transposed to the new bar:

| | Long (short is the mirror) |
|---|---|
| Trigger | close above the highest high of the previous *N* bars |
| Flow 1 | bar volume >= *k* x its 20-bar average |
| Flow 2 | aggressive-buy share of the bar >= 55% |
| Flow 3 | open interest up over the signal bar (1h or 4h), measured from the lagged 5-min series |

| Parameter | Values |
|---|---|
| *N* | {20, 48} |
| *k* | {1.5, 2.5} |
| stop *s* | {1.0, 1.5} x ATR(14) |
| target *r* | {1.5, 2.0} x stop |
| time stop *T* | **fixed**: 24 bars on 1h (1 day), 12 bars on 4h (2 days) |

**Search budget:** 4 entry x 4 exit x 2 directions x 2 timeframes = **64 combinations exactly**. No family, filter, parameter or timeframe is added after results are seen. Long and short are separate candidates.

**Control (reported, not a candidate):** the same grid with the three flow filters removed (plain N-bar breakout). It answers whether order flow adds anything over the breakout itself. It cannot pass or validate anything.

## 7. Gates

Minimum trade counts differ by timeframe because 4h fires about a quarter as often. They are set here, before running, not after.

### Stage 1: dev coins x dev period

1. **Trades:** >= 150 on 1h, >= 60 on 4h; trades on at least 10 of the 15 dev coins.
2. **PF >= 1.15** at base costs.
3. **PF >= 1.05 at 2x costs.**
4. **Positive expectancy on at least 9 of 15 dev coins.**
5. **Beats random entry:** same exits, costs, coins and trade count, random entry times, 200 runs; candidate expectancy above the 95th percentile.

### Stage 2: walk-forward inside the dev period (dev coins only)

- Folds: train 6 months, test next 2, step 2 → 6 test folds covering 2025-03 to 2026-03.
- Selection per fold, within direction x timeframe: highest training PF among combos with **>= 30 trades (1h) / >= 12 trades (4h) and PF >= 1.10**. If none qualifies, the fold trades nothing and scores 0.
- **Pass:** total out-of-sample R > 0 **and** at least 4 of 6 folds positive, base costs.

### Stage 3: robustness (dev coins x dev period)

6. **Parameter neighbours:** each parameter moved one step within the grid still gives PF > 1.0 at base costs.
7. **Human delay:** entry **30 minutes late** (the open of the 15m bar starting 30 min after the signal bar closes) still gives PF > 1.0 at base costs.
8. **Not one coin:** removing the single best coin leaves PF >= 1.10.

### Stage 4: sealed quadrant (holdout coins x sealed period), run ONCE

At most 5 combinations (highest walk-forward OOS R if more survive).

9. **Trades:** >= 50 on 1h, >= 20 on 4h.
10. **PF >= 1.10** at base costs.
11. **PF >= 1.00 at 2x costs.**

## 8. Decision rule

> **A combination is `validated`, and becomes a desk card, only if it passes all 11 gates.** Everything else is rejected and never appears on the panel. No partial credit, no re-running with looser thresholds.

## 9. After validation (unchanged from the last pre-registration)

- Card expiry: 2 bars of its timeframe (2h on 1h, 8h on 4h).
- Every card graded automatically, accepted or passed.
- Demotion: after 100 graded cards, realised expectancy below 0 R after base costs removes the setup.
- Frequency reported, not gated.

## 10. What I expect (written before running)

- Taker costs as a share of R should fall to roughly **0.10 R per trade on 1h and 0.05 R on 4h** (from ~0.15 R on 30m). That only helps if the gross edge per trade holds up at the longer timeframe, which is unknown.
- **Most likely outcome: 1h fails at 2x costs (the same churn failure, slightly less severe); 4h has the best chance on cost grounds but may fail on trade counts** — 15 coins x 19 months at 4h is a small sample, and the 4h gates have less statistical power. A 4h pass should be read with that caveat.
- Shorts: expected to do worse than longs (every standalone short in this project has failed), but tested on the same terms.

## 11. Outputs

- `research/desk1h4h_run.py` — one script, one seeded run (seed 20260928), records this file's SHA-256 in every output.
- `research/results/desk1h4h_stage1.json` … `_stage4.json`, plus `desk1h4h_control.json`.
- `research/DESK1H4H_REPORT.md` — every combination and the gate it failed.
- Only if something validates: `user_data/desk/setups.json` gains the exact rules for the live scanner.
