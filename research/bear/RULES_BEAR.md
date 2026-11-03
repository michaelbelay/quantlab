# Bear strategy rules (fixed 2026-11-01, before any new run)

Goal: strategies that **earn while the market falls**, for the 300 USDT Binance USDT-M futures account, run by
quantlab's own trader. These rules apply to every bear idea from today on. They are not changed after a result is seen.

## 1. What "bear" means
- **Bear day** = BTC 20-day return <= 0 at the last completed UTC daily close (the same rule as the UI Today view).
- **Bear-Wild / Bear-Calm** = bear day with BTC 20-day volatility above / at or below its 365-day median (UI rule).
- A bear strategy trades **only on bear days** (it may name Bear-Wild or Bear-Calm only). On other days it is flat.
- Shorts are the main tool. No dip-buying longs ("what if there is a real crash"): a long is allowed only as a hedge
  inside a market-neutral book, never as a bounce bet.

## 2. Coins and data
- Coins: `configs/universe_coins.json` + `configs/live_coins_2026-10.json` (134 together) **minus memes** (1000PEPE,
  FARTCOIN, PENGU, TRUMP, WIF) = 129 coins. DOGE stays. The list is fixed; no other coin set is used to judge a result.
- Candles: `data/market/main/binance/futures` 1h + funding, **2022-01-01 → 2026-09-30** (includes the 2022 bear year).
- Split in two halves for the luck check: **A 2022-01-01 → 2024-04-30**, **B 2024-05-01 → 2026-09-30**.
- A coin counts only while it has data and >= 10M USDT traded in the last 24h.

## 3. Simulation (same for every idea)
- Signal on the closed candle, entry at that close. No look-ahead (indicators use closed candles only).
- Costs: 0.20% per round trip (fee 0.05% + slippage 0.05% each side). Also run at **2x costs**.
- **Funding counted** from the real history (shorts receive positive funding, pay negative).
- Every trade has a hard stop. Inside a candle the stop is checked before the target (worst case).
- One trade per coin at a time.

## 4. Registration
- Before each run: a `REGISTER_<name>_<date>.md` in `research/bear/` with the idea, every threshold, stop / target /
  hold, and the expected trade count. Thresholds are fixed there and **never re-tuned** after the run.
- A changed idea is a **new** idea with a new register. Every run is counted in `python -m quant.trials`.
- Extra diagnostics after a run (why it failed) are allowed, report only, no re-tune.

## 5. Gates
**Step 1 – signal test (no slot limit)**, bear days only:
- >= 150 trades in total and >= 50 in each half
- average net trade (costs + funding) >= +0.30% in **both** halves
- still positive at 2x costs over the whole period
- >= 55% of bear months positive

**Step 2 – 300 USDT account test** (quantlab replay, 6 slots, the trader's real sizing and minimum orders):
- profit at base and 2x costs, max drawdown <= 35%, no single trade losing > 10% of the account

**Step 3 – paper forward** on the quantlab paper trader, live data:
- >= 30 trades on >= 10 bear days, day average > 0, worst open trade shown alongside the closed result

| Class | Meaning |
|---|---|
| 🔴 | fails step 1 |
| 🟠 | passes step 1 only |
| 🟡 | passes steps 1 + 2 – goes to paper |
| 🟢 | passes steps 1 + 2 + 3 – Michael decides on live (he starts real money himself) |

## 6. Reporting
- Closed and open P&L together, worst trade first, results by half and by year (2022 shown separately).
- Plain numbers, no "winning strategy" wording before 🟢.

## 7. Already tested – not repeated in the same form
Bear batch 2026-10-24 (10 ideas, all 🔴: rally_short, retest_short, fade_breakout, crash_bounce, flush_long,
weak_short, leader_long, pump_fade, bear_rally_short, xs_basket), crash short 2026-10-22, downtrend study 2026-10-07,
bear-calm short book 2026-10-12, short sweeps 2026-09-24. Incubator still running forward: dn_coil_short.
Note: those tests used 2024-04 → 2026-09 without funding; they are not re-run under these rules unless Michael asks.

## Amendment A1 (2026-11-01, after batches 1–3, before the exploration scan)
Michael: "focus on our coin list", "find a bearish short trade ... be open to explore ideas".
- Coins from now on: the trader's list (`trader/settings.py` COINS) minus 1000PEPE (no memes except DOGE) = 19 coins.
- Open exploration is allowed as a **registered grid scan** (`REGISTER_BEAR_EXPLORE_2026-11-01.md`): many short
  variants on 2022-01 → 2026-03, the last 6 months (2026-04 → 2026-09) held back and looked at once, only for the
  scan's top 5. Gates for the scan are written in that register. Steps 2 (300 USDT replay) and 3 (paper) unchanged.

## Amendment A2 (2026-11-01, after batch 5, before batch 6)
Michael: "I will not accept anything other than a good strategy on our coin list in the bearish market".
After 23 single ideas and a 252-variant scan, a pass by luck is likely, and batch 5's X6 passed while 84% of its profit
came from 3 months and its shorts lost. From batch 6 on, step 1 also needs these **robustness gates**:
- the best 3 months carry <= 50% of the total net profit
- average net is still > 0 without the 10 best trades
- >= 3 of the 5 calendar years 2022–2026 have a positive average net
- for a pair or basket with long hedges: the short side alone has a positive average (the strategy must earn from the fall)
A candidate is reported to Michael only after it passes step 1 (with these gates) and step 2. X6 stays 🟡 under the old
gates; it fails the new ones (3-month share 84%, short leg -0.20%) and is not put forward.

## Amendment A3 (2026-11-01, after batch 8, before batch 9)
38 short ideas, the scan and 3 discovery rules all failed; the drift table (batch 8 register) shows coins rose after
bear days except deep bear in 2022. Batch 9 therefore tests **longs in a shallow bear with a crash guard** (no entry in a
deep bear; exit at the first daily close that turns deep). This departs from §1 ("no dip-buying"), which is Michael's
rule: batch 9 is reported to him for a decision and is not put on paper without his OK. The regime split was seen in the
drift table before registering (said openly). Gates A2 apply (the short-side gate does not apply to longs).
