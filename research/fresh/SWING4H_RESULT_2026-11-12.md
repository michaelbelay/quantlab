# 4h swing runs, 2026-11-12 — result

Executes `REGISTER_SWING4H_2026-11-12.md` and `REGISTER_S7_4H_2026-11-12.md`. Ten runs, every one registered
before it ran, every one reported here. Nothing was re-tuned after a result. Engine `research/fresh/swing4h.py`,
panel `data/cache/panel4h_*.parquet` (261 coins, 10,404 4h bars, 2022-01-01 → 2026-09-30, real funding).

**Engine check before any market data:** 8 synthetic price paths — flat price costs exactly the round trip, a 5%
fall earns 5% minus costs, a wick through the stop fills at the stop, a gap beyond it fills at the open, funding
accrues to the short, the market-neutral book charges both legs. All passed (`swing4h.py selftest`).

## 1. The deep-bear short family (W1–W5) — all fail

| id | what | trades | avg net | half A | half B | at 2x | step 1 |
|---|---|---|---|---|---|---|---|
| W1 | cdeep_funding, bear-day gate | 3,611 | −0.024% | **+0.651%** | **−0.456%** | −0.224% | fail |
| W2 | same, no BTC gate | 5,615 | +0.045% | −0.058% | +0.112% | −0.155% | fail |
| W3 | W1 market-neutral vs BTC | 3,637 | −1.356% | −0.779% | −1.726% | −1.756% | **withdrawn, engine fault** |
| W4 | W3 with no stop | 3,526 | −0.230% | +0.412% | −0.648% | −0.630% | fail |
| W5 | W1 with no stop | 3,526 | −0.032% | **+0.798%** | **−0.572%** | −0.232% | fail |

**Two findings worth more than the table.**

1. **This was never a carry trade.** All 3,611 W1 entries have a funding rate of exactly **+0.0100%** — Binance's
   default. `FUND >= 0.0001` means "funding is at its baseline", not "longs are crowded". Across the whole panel,
   funding is above 0.02% on only 5.1% of coin-bars and above 0.05% on 1.4%. The carry actually collected is
   **+0.03% per 3-day trade**, against a 0.20% round trip. The cdeep family is a trend short wearing a carry label.
2. **The edge died in April 2024, and it is not about the stop or the hedge.** Every variant — with a stop, with no
   stop, hedged, unhedged, bear-gated, ungated — is positive in half A and negative in half B. Shorting coins in
   their own deep bear paid in 2022 → 2024-04 and has lost since.

W3 is withdrawn as my error, not a market result: its pair stop triggers when the coin's high and BTC's low fall in
the same 4h bar and then fills at **both** extremes at once, so its stop exits average −10.8% against an 8% stop.
W4 is the honest version (no stop at all) and gives −0.230%. A correct intrabar pair stop needs 15m path data.

**What this means for the bear lab:** it is still generating cdeep_* variants daily (24 ideas on paper, 98 screens).
On 261 coins over 4.75 years the mechanism does not hold up. The 19-coin screen it passed is the trader's own
large-cap list, chosen in 2026 — the result does not survive a wider universe.

## 2. S7 "dip in uptrend" (S7a–S7c) — the only survivor, and it is dormant

S7-PIT is the lab's one out-of-sample pass (settings frozen on 2021-2023, then +1.26%/trade, PF 1.53 on
2024-01 → 2026-09) and the register said "not coded as a bot yet". Frozen settings, unchanged:
dip 1.5σ, hold 72h, stop 3σ, trend 10 days.

**S7a — replication check on the original's top-10 point-in-time universe.** On the original's own test window my
4h engine gives **200 trades, +1.274%/trade, PF 1.57** against the recorded 1h **435 trades, +1.26%, PF 1.53**.
Average and profit factor match; the 4h version sees fewer dips than the 1h version, as expected. The engine is a
fair translation.

**S7a passes every step-1 gate** — the first thing in this lab to do so on registered gates:

| | whole window | half A | half B |
|---|---|---|---|
| trades | 322 | 141 | 181 |
| avg net | +1.015% | +1.373% | +0.736% |
| **with the top 1% of winners removed** | +0.472% | **+0.850%** | **+0.178%** |
| at 2x costs | +0.815% | | |
| months positive | 55.1% | | |

300 USDT, 6 slots, 1x: **300 → 509**, max drawdown **−20.4%**, positive in every year except 2022.

**S7b / S7c — widening the universe fixes frequency and breaks the edge.** On all 261 coins: 3,972 trades,
**16 a week in 85% of weeks** (the consistency rule's frequency, solved) and +1.109%/trade. But:

- remove the top 1% of winners and **half B goes to −0.458%** — in the recent half the entire result is 40 trades
  out of 2,702, led by ALPACA +578% (a one-off squeeze), AKE +237%, BULLA +171%;
- the account drops **−68%** and spends 46 weeks under its high;
- months positive in half B: 34.5%.

S7c was the registered attempt to separate the two: a liquidity ladder (10 / 50 / 100 / 250 / 500M USDT) chosen on
**half A only** by trimmed average, then one look at half B. Half A does not separate them — every threshold gives
a trimmed +1.24% to +1.73% — so the rule picked 10M, i.e. S7b, and half B came back at **−0.458% trimmed**. Failed.

**Reading:** on the wide universe, dip-buying in 2024-2026 is an outlier harvester, not an edge. On liquid coins
the edge is real and survives trimming in both halves, but it is small and it has stalled: avg net per trade
**2025 −0.35%, 2026 +0.03%**, and 92.7 weeks under its last equity high. It needs an uptrend, and it has not had one.

## 3. Where this leaves the project

- **Stop spending the bear lab's daily compute on cdeep variants.** Five registered runs on 14× the universe say the
  mechanism is a 2022-2024 effect. (The lab's own 2026-11-01 summary already said shorts only paid in crash months.)
- **S7a is the one candidate worth a paper forward test.** It passes step 1, survives trimming in both halves, has a
  −20.4% drawdown at 1x, and is already written as code. Its honest weakness: it is a long strategy that sits in
  cash in a bear, it trades 1.3 times a week, and it has made nothing for two years.
- **No bear strategy was found today**, and nothing here contradicts the lab's record of 0 validated families.
- The engine is reusable: any 4h swing idea now runs over 261 coins in about 10 seconds
  (`python research\fresh\swing4h.py <variant>`), with real funding and the registered cost model.

## 4. Trials
10 counted runs: W1, W2, W3, W4, W5, S7a, S7b, S7c (and the S7c ladder is 5 threshold runs on half A, of which one
was carried to half B). Trade lists: `research/fresh/swing4h_*_trades.csv`. Summary: `swing4h_results.json`.
