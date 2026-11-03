# Bear discovery: learn on half A, test once on half B (registered 2026-11-01, before the run)

Rules: `RULES_BEAR.md` + A1 + A2. Michael: "I will not accept anything other than a good strategy on our coin list in
the bearish market". After 34 hand-written ideas, this run lets the data pick the conditions, but **only from half A**
(2022-01-01 → 2024-04-30). Half B (2024-05-01 → 2026-09-30) is used once, to test the picked rules. Nothing changes after.

## Sample and trade
- Every coin (19) at every daily close (23:00 bar) where tomorrow is a bear day and the coin passes the volume filter.
- Trade: short at that close, stop 8% (checked first), exit after 72h; 0.20% costs + real funding.

## Features (all known at the close)
Coin: 1-, 3-, 7-, 30-day return; 7-day return minus BTC's; distance to 20- and 50-day average of daily closes; 7-day
volatility (1h returns) and its ratio to 30-day volatility; last funding; 7-day funding sum; perp buy share 24h and 7d
(rank vs previous 720h); 24h volume / average daily volume of 30 days; daily RSI14; distance to 30-day high and low.
Market: BTC 1- and 7-day return; deep bear (0/1); BTC DVOL rank (90 days) and 3-day DVOL change; day of week.

## Picking (half A only)
1. Each feature is cut into 5 equal-count buckets (edges from half A). A **single rule** = "feature in bucket q".
2. A **two-part rule** = two single rules from different features that both hold.
3. A rule qualifies on half A if: >= 100 trades (overlapping windows counted, as a rough screen), average net >= +0.50%,
   and average net > 0 in both 2022 and 2023-01..2024-04.
4. Rank qualifying rules by t-stat on half A. Pick the **top 3 with no feature in common** (single or two-part).

## Test (half B, once, proper trades: one trade per coin at a time)
Each picked rule passes if on half B: >= 50 trades, average net >= +0.30%, > 0 at 2x costs, >= 55% of months positive,
average net > 0 without its 10 best trades, best 3 months <= 50% of the profit.
Then RULES_BEAR step 2 (300 USDT, 6 slots of 50 USDT, hourly open P&L) on the full period. Pass → 🟡 → paper (Michael's OK).

## Stated before the run
- Many rules are screened on half A; that is why half B is the judge. Half B has been seen by earlier single ideas
  (not by this procedure); that is a weakness, said now. Paper is the final judge.
- Counted as 3 trials (the 3 picked rules).

## Result
Run 2026-11-01, `bear_discovery.py`, rules unchanged. 590 rules qualified on half A; the 3 picked all fail half B → 🔴.

| picked on half A | half A trades / avg | half B trades / avg | B 2x | B months + | B w/o 10 best | verdict |
|---|---|---|---|---|---|---|
| DVOL rank 0.07–0.20 & DVOL 3-day change >= +5% | 127 / +3.47% | 162 / -0.74% | -0.94% | 3/7 | -1.55% | 🔴 |
| coin 7d vol lowest fifth & BTC 1d return -2.4%..-0.6% | 132 / +2.10% | 138 / -0.40% | -0.60% | 6/26 | -1.26% | 🔴 |
| BTC 7d return >= +0.7% & Wednesday | 151 / +2.82% | 204 / +0.85% | +0.65% | 6/10 | +0.21% | 🔴 (best 3 months 154% of profit) |

What half A finds in short conditions does not carry over to half B.
