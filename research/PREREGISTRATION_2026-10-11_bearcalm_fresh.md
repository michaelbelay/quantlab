# VBreak4 shorts in Bear-Calm, on coins VBreak4 never ran on — pre-registered 2026-10-11

Written before any return on these coins is computed. Run once; no re-runs, no changes after seeing results.
Michael's go: "yes go ahead with that test" (2026-10-11).

## Why
The live bot (VBreak4 Bull-Calm) opens trades on ~30% of days and holds cash otherwise. Bear days are ~48% of the
time and nothing tested earns in them (downtrend rules, flush bounce, funding shorts, MajorsTrend shorts: all 🔴).
The one hint left: in the 2026-10-11 conditions test, Bear-Calm VBreak4 was close (PF 1.18, failed on DD 43%), and
its short side was stronger than its long side. That split was seen AFTER the fact, on all 413 coins, so it cannot
be judged on them. This test asks whether it holds on coins VBreak4 has never been run on.

Context only, NOT evidence (already seen, 2021-26, 413 coins, top-133 point in time, VBreak4Both both directions):
Bear-Calm shorts 2,181 trades PF 1.32; Bear-Calm longs 1,186 trades PF 0.89.

## Strategy (frozen, nothing tuned)
VBreak4Both = pipeline candidate `focus-val1-vbreak4both` (`research/pipeline/focus/validate_promising.yaml`) with
ONLY the direction changed to `short` (a shorts-only bot):
spec {family: volatility_breakout, params: {bars: 4, atr_mult: 2.0}, filters: [btc_regime, volume], trend_mode: with,
direction: short}; cfg {leverage: 1.0, stop_mode: atr, stop_atr: 2.0, tp_mode: none, entry_mode: instant, max_bars: 400}.
Engine `research/engine` (`simulate_pair`), base costs fee 0.05% + slippage 0.05% per side + funding.
2x costs = pnl − 0.20 per 100 USDT notional (as in the conditions test).

## Coins: fresh for VBreak4
Every USDT perpetual in the Binance public archive (`user_data/rotation_data`, 859 symbols, delisted included) minus
the 133 VBreak4 development coins minus the 280 unseen coins (both already ran VBreak4) minus stablecoins / index
contracts (BTCDOM, DEFI, BFUSD) minus non-crypto underlyings (exchangeinfo_underlying_2026-10-04.json) minus files
with < 400 hourly bars. = 266 coins (list frozen in `research/bearcalm_fresh/coins.json`).
These coins are mostly young (listed 2024+) and smaller. Some (1000PEPE, ARK, RARE, SAGA, RAY) were used by other
research, never by VBreak4. Full 1h OHLCV downloaded from data.binance.vision (public, no key) into
`user_data/fresh_data/`; funding copied from rotation_data.

## Point-in-time universe (no hindsight)
A trade counts only if, on its entry day, the coin ranks <= 133 by average daily quote volume over the previous 30
days (rank among ALL 679 crypto coins = 133 + 280 + 266; same formula as `C:\quantlab\quant\liquidity.py`, source
rotation_data quote_volume, known at the start of the day).

## Condition and period
Bear-Calm exactly as `research/vbreak_conditions.btc_conditions()` (BTC 20d return <= 0 and 20d vol <= its previous
365-day median; last completed daily close before entry). Entries 2024-01-01 → 2026-09-25 (data end). Engine runs on
full history for warm-up; only entries in the period count.

## Pass rule (all required)
1. >= 100 trades (fewer = not enough evidence = fail)
2. PF >= 1.15 at base costs and PF >= 1.05 at 2x costs
3. positive net in >= 2/3 of calendar years with >= 20 trades
4. still positive after removing the 3 best entry days (crash-cluster check, the flush lesson)
5. 300 USDT book trading only these trades (`C:\quantlab\quant\book.py` replay: 20 slots, <= 10 same direction,
   stake = equity/20, 1x, real minimum orders, default 5 USDT where unknown): ends above 300 and max drawdown <= 30%
   (30% = the live strategy's tested worst drop; a bear add-on must not be riskier than what runs now).
One trial (+1). Reported regardless: trades per year, per-coin concentration, the 300 USDT curve.

## Decision
Pass → 🟡: paper trading on live data (never real money first); Michael decides later.
Fail → 🔴: the answer for Bear markets is cash; the Today tab already shows that. No variant of this idea is tested on
these coins again.
Runner: `research/bearcalm_fresh.py` → `research/BEARCALM_FRESH_RESULT_2026-10-11.md` + `bearcalm_fresh/result.json`.
