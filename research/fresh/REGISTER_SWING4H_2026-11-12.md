# Swing on 4h bars, full universe - registered before the run (2026-11-12)

Michael 2026-11-12: "not year wise, swing trade 4hrs chart, few days strategy ... I want a solution".

The idea is NOT new. `cdeep_funding` (bear lab, written 2026-11-02) passed its history screen and is positive on
live paper. Its only failure is **frequency**: on the trader's 19 coins it fires on about 14 days a year, so it
fails CONSISTENCY_RULE_2026-11-11. The fix tested here is the universe, not the rule: the same rule on the
**261 coins that have 4h data**, on 4h bars. Precedent: RULES.md amendment A1 re-ran families **unchanged** on the
full coin set. The rule, the hold, the stop and the thresholds below are copied from the idea as it stands and are
**not re-tuned after the run**.

## Data (fixed now)
- `data/market/main/binance/futures/*-4h-futures.feather` + `*-1h-funding_rate.feather`, cached as
  `data/cache/panel4h_*.parquet` (built 2026-11-12, builder `build_panel.py`, printed 261 coins / 10,404 bars).
- Window **2022-01-01 -> 2026-09-30** (4h). Halves for the luck check, as RULES_BEAR: **A 2022-01-01 -> 2024-04-30**,
  **B 2024-05-01 -> 2026-09-30**.
- A coin counts at a bar only while it has >= 1,200 closed 4h bars (200 days) of history **and** its 24h traded
  value over the previous 6 closed bars is >= 10M USDT.
- **Known bias, stated before the run:** the folder holds coins that are listed today. Perps delisted before today
  are absent. For a SHORT strategy that removes the worst-performing coins, so the test is biased **against** the
  result reported here, not in its favour.

## The rule (copied from research/bear_lab/ideas/cdeep_funding.py, hours -> 4h bars)
At the close of each 4h bar, for each eligible coin:
1. **own deep bear** - close < MA(1,200 bars = 200 days) **and** that MA is below its own value 120 bars (20 days) ago;
2. **paid to be short** - the last funding rate known at this bar close >= **+0.01%** (0.0001);
3. **under its trend** - close < EMA(120 bars = 20 days).
All three true -> **SHORT at this bar's close**.
- Hold **18 bars = 72 h = 3 days**. Hard stop **8%** against. No target.
- One trade per coin at a time; after a trade on a coin closes, **18 bars** before that coin may signal again.
- Exits inside a bar: the **stop is checked first** (worst case). A bar that opens beyond the stop fills at its open.

## Variants (all three fixed now; three trials, counted)
| id | difference |
|---|---|
| **W1** | the rule above, entries only on **bear days** (BTC 20-day return <= 0 at the last completed UTC daily close) - the RULES_BEAR gate |
| **W2** | the rule above with **no BTC gate** (the coin's own deep bear is the only market condition) |
| **W3** | W1's signal, **market-neutral**: short the coin and long the same notional of BTC, same 18-bar hold, stop when the pair is 8% against. This targets the recorded reason the 19-coin shorts failed ("after a bear day the coins rose") |

## Costs and funding (fixed now)
- **0.20% per round trip** (fee 0.05% + slippage 0.05% per side); W3 pays it on both legs (0.40%).
- Every run is reported again at **2x costs**.
- **Real funding**: every funding stamp inside the holding window, rate x the price at that stamp x the position.
  A short receives a positive rate and pays a negative one. W3's BTC leg pays its own funding.

## Gates (RULES_BEAR step 1, unchanged)
- >= 150 trades, and >= 50 in each half;
- average net trade (after costs and funding) **>= +0.30% in both halves**;
- still positive at **2x costs** over the whole window;
- **>= 55%** of bear months positive.

## Frequency and regularity (CONSISTENCY_RULE_2026-11-11, the reason this run exists)
- W1 and W3 are bear-only: entries on **>= 25% of bear days** and **>= 40 trades per year** of history.
- W2 is all-market: **>= 3 trades per week** on average and at least one trade in **>= 80% of weeks**.
- Both: **>= 60% of calendar months positive**, every full calendar year positive, the best 3 entry days make at
  most **25%** of total profit.

## Step 2 - only for a variant that passes step 1
300 USDT, **6 slots**, stake = equity / free slots, 1x, one trade per coin. When more signals appear at one bar
than there are slots, they are taken in order of **highest funding rate first** (most paid to be short) - fixed
here, before any result. Report: equity curve, max drawdown, longest stretch under the last equity high, by year
and by half.

## Reporting
Whatever the run gives is written into `research/fresh/SWING4H_RESULT_2026-11-12.md` unchanged. No threshold above
is moved afterwards; a changed rule is a new idea with a new register.

## Amendment, same day, AFTER the W1-W3 results, BEFORE W4/W5 were run

Two things the first run showed:
1. **The funding condition does not select anything.** Every one of the 3,611 W1 entries has a funding rate of
   exactly +0.0100% - Binance's default. `FUND >= 0.0001` is "funding is at its baseline", not "longs are crowded".
   The carry actually received is +0.034% per 3-day trade. This idea was never a carry trade.
2. **The W3 pair stop is invalid and the fault is in the engine, not the market.** It triggers when the coin's high
   and BTC's low occur in the same 4h bar and then fills at BOTH extremes at once. Its stop exits average -10.8%
   against an 8% stop, which is impossible for a real stop. W3's headline number is an artefact and is withdrawn.

Rather than invent a better stop convention after seeing results (that would be tuning), the stop is **removed**:

| id | rule |
|---|---|
| **W4** | W3 exactly - short the coin, long the same notional of BTC - with **no stop**; every trade exits at the 18-bar (72 h) hold. Costs 0.40%, both legs' real funding. |
| **W5** | W1 exactly - short the coin alone - with **no stop**; exit at the 18-bar hold. Costs 0.20%. |

A correct intrabar pair stop needs the pair's path inside the bar (15m data exists and is untouched); that is a
separate idea for a separate register, not part of this one.

**How a winner is chosen, fixed now:** any choice between W4 and W5, or of any filter, is made on **half A
(2022-01-01 -> 2024-04-30) only**. Half B (2024-05-01 -> 2026-09-30) is looked at **once**, afterwards, as the test.
Gates on half B: average net >= +0.30%, positive at 2x costs, >= 55% of months positive, and the consistency rule.
