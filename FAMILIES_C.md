# Protocol C families (registered before running; code: strategies/families_c.py)

## Batch 1 (2026-10-05) — one setting each, run on 1h (413 coins) and 15m/30m (30 desk coins)
| ID | Family | Long / short rule | Exit (stop / TP in ATR, max hold) |
|---|---|---|---|
| C01 | Donchian breakout | close above / below the prior 20-bar channel | 2 / 4, 2 days |
| C02 | Volatility squeeze → expansion | BB width in lowest 20% of 100 bars, then close outside the band | 1.5 / 3, 1 day |
| C03 | EMA pullback continuation | EMA50 vs EMA200 trend; dip to EMA20 and close back beyond it | 1.5 / 3, 2 days |
| C04 | RSI(2) reversion with trend | RSI2 < 10 above EMA200 / > 90 below EMA200 | 2 / 1.5, ½ day |
| C05 | VWAP reversion | > 2.5 ATR from 1-day rolling VWAP, fade | 2.5 / 1.5, 1 day |
| C06 | Volume-confirmed breakout | 20-bar breakout with volume > 2× average | 2 / 4, 1 day |
| C07 | Volume-delta divergence (15m/30m) | price down > 2 ATR over a day while taker buying dominates → long; mirror | 1.5 / 3, ½ day |
| C08 | Funding-extreme fade | 24h funding z > 2 at a 3-day high → short; z < −2 at a 3-day low → long | 2 / 3, 2 days |
| C09 | Relative strength vs BTC | beat BTC by > 2 ATR% in a day while BTC > EMA200 → long; mirror | 2 / 4, 2 days |
| C10 | Session (Asia-range) breakout | first close beyond the 00–08 UTC range, 08–20 UTC | 1.5 / 3, ⅔ day |

### Batch 1 DEV result (2026-10-05) — all 30 runs FAIL
- 15m / 30m: every family PF < 1.0 after costs (0.2% round trip vs small moves). C08 30m: PF 1.05, twin p100,
  shorts PF 1.21.
- 1h, ALL 413 coins: consistent long/short asymmetry — SHORT side profitable in 6 families (C10 1.21, C06 1.14,
  C01 1.13, C08 1.10 with twin p100, C02 1.09, C09 1.05); LONG side 0.78–0.87 everywhere.
- Diagnosis: on a point-in-time universe (incl. dying coins) downside breakouts continue, upside breakouts fade.

## Batch 2 (2026-10-05, before running) — mutation targeting the diagnosis; exits unchanged from batch 1
| ID | Rule |
|---|---|
| C11 | C01 short side only (Donchian breakdown) |
| C12 | C06 short side only (volume-confirmed breakdown) |
| C13 | C10 short side only (session breakdown) |
| C14 | C08 short side only (funding-extreme fade at a 3-day high) |
| C15–C18 | C11–C14 each hedged: BTC long of equal notional for the same holding (equal long/short exposure); hedge leg pays its own costs and funding. Not applied to BTC itself. |

### Batch 2 DEV result — all FAIL; diagnosis
- C11 Donchian breakdown short 1h: 300 → 1,697, PF 1.151, but random-timing twins beat it (twin p2) and the BTC-hedged
  version (C15) loses → the batch-1 "short edge" is mostly alts falling vs USDT in 2021-24 (beta), not timing.
- C14 funding-extreme fade, short only: twin p100 on 1h and 30m and still positive hedged (C18) → real timing
  information. 1h: PF 1.142 (gate 1.15), x2 1.035, DD 11.4%, 2,141 trades, 3/4 periods +. 30m: PF 1.208, DD 3.3%, 164 trades.

## Batch 3 (2026-10-05, before running)
| ID | Rule | Exit |
|---|---|---|
| C19 | C14 + stall confirmation: signal bar closes below the previous bar's low | as C14 (2 / 3 ATR, 2 days) |
| C20 | C14 with a longer unwind window | 2 / 5 ATR, 4 days |
| C24 | Pump fade (short): 24h return ≥ +15% and 24h volume > 2× its 7-day daily average | 3 / 4 ATR, 2 days |
| C25 | Capitulation bounce (long): 24h return ≤ −15%, volume > 2× 7-day average, 24h funding < 0 | 3 / 4 ATR, 2 days |
| C26 | C24 + C25 together (long and short) | 3 / 4 ATR, 2 days |

### Batch 3 DEV result — all FAIL; diagnosis
- C19 produced no trades: my rule was contradictory (a close at a 3-day high cannot close below the prior low). Design error.
- C20 (longer unwind): weaker than C14 (PF 1.03). C24 pump fade: no edge (PF 0.89–1.0).
- C25 capitulation bounce (long): desk coins 15m/30m PF 2.5–2.7, DD ~3%, twin p100, but only 62–86 trades; on ALL 413
  coins at 1h it fails (PF 0.8, twin p2) → works on liquid coins only; small/dying coins keep falling.
- C26 (C24+C25) 15m: PF 1.19, x2 1.10, DD 6.6%, 422 trades, twin p100 — failed top-coin share (31%); all profit from longs.

## Batch 4 (2026-10-05, before running) — liquidity filter + mirrored crowding condition
Liquidity: point-in-time rank of 30-day average daily traded volume across ALL 413 coins (data/liq_rank.parquet,
yesterday's data only); eligible = rank ≤ 40. Thresholds fixed: ±15% in 24h, volume > 2× 7-day average.
| ID | Rule | Exit |
|---|---|---|
| C27 | C25 (capitulation long: −15%/24h, volume spike, 24h funding < 0) on liquid coins only | 3 / 4 ATR, 2 days |
| C28 | Crowded pump fade (short): +15%/24h, volume spike, 24h funding > 0 and its z-score > 1, liquid coins only | 3 / 4 ATR, 2 days |
| C29 | C27 + C28 (long and short) | 3 / 4 ATR, 2 days |
| C30 | C29 with a BTC hedge per trade (equal long/short exposure) | 3 / 4 ATR, 2 days |

### Batch 4 DEV result — all FAIL; diagnosis
- C27 capitulation long on liquid coins, 1h 2021-24H1: PF 0.79 (245 trades) → the desk 15m/30m result (PF 4.5–4.8,
  35–41 trades) is two 2025 crash clusters, not an edge. C28 crowded pump fade: no edge (PF 0.83–1.0).
- Running summary after 27 families / 81 runs: 15m/30m dominated by costs; 1h short-breakout profit is alt beta;
  capitulation is event clustering; **funding crowding (C14) is the only signal with repeated timing evidence.**

## Batch 5 (2026-10-05, before running)
| ID | Rule | Exit |
|---|---|---|
| C31 | C14 on liquid coins (rank ≤ 40) | as C14 |
| C32 | C14 with z > 2.5 (more extreme) | as C14 |
| C34 | Long counterpart with regime: 24h funding z < −2 at a 3-day low AND BTC above its 200-bar EMA | 2 / 3 ATR, 2 days |
| C36 | Settlement timing short: previous funding event ≥ +0.05%; short at the close of the bar 3h before the next 00/08/16 UTC settlement | 2 ATR stop, no TP, 4 bars (exit 1h after settlement); 1h only |
| C37 | Mirror long: previous funding event ≤ −0.05% | same; 1h only |
| C38 | C36 + C37 | same; 1h only |

### Batch 5 DEV result
- **C32 PASS DEV** (1h, ALL coins): short at 24h funding z > 2.5 at a 3-day high. PF 1.16, x2 1.05, 300 → 395,
  DD 10.4%, 4/4 periods positive (2022 +0.06), twin p100, 1,631 trades.
- C31 (liquid only): PF 1.138, fails PF gate. C37 settlement long: PF 1.044, 4/4 periods +, twin p100 — thin.
- C34, C36, C38 fail.
- **C32 FAIL VALID** (2024-07 → 2026-03): 300 → 272, PF 0.921, x2 0.863, DD 21.8%, 698 trades. Periods: 2024H2 −8,
  2025H1 −33, 2025H2 +4.5, 2026Q1 +8.2. Diagnosis: shorting crowded longs lost through the late-2024 rally
  (crowded longs kept winning), recovered once that regime ended. Same regime sensitivity as F9/F17/F18.
  Note: any family designed from this diagnosis has seen VALID indirectly → it must be judged walk-forward
  on unseen time and by forward paper testing, not by VALID again.

## C39 = C32 + market-wide OI drop > 3% in the prior 1h (user-specified, 2026-10-05) — KILLED
Market OI = 30-coin basket from the Binance archive (BTC only before 2021-12). Dev: 20 trades, PF 0.59, twin p20.
Validation: 1 trade (win), twin p94. Fixed rule (validation PF > 1.05 AND beats twins) → KILL. Not iterated.

## C40 = C32 + MajorsTrend regime gate (user-approved 2026-10-06, registered before running)
Idea: combine the live 🟢 MajorsTrend (long-only, wins when majors trend up) with the crowding short
(C32, lost when crowded longs kept winning in the late-2024 rally). The short trades only while
MajorsTrend's BTC leg is OUT of the market.
| ID | Rule | Exit |
|---|---|---|
| C40 | C32 unchanged (short: 24h funding z > 2.5 at a 3-day high, all coins, 1h) AND BTC 20-day return <= 0 at the last completed UTC daily close (the live MajorsTrend BTC rule, 2026-10-04) | as C32 (2 / 3 ATR, 2 days) |
One setting. No grid, no alternative lookback, no ETH/BNB variant chosen afterwards.

Honesty note: the gate was motivated by C32's VALID failure, so VALID (2024-07 -> 2026-03-25) is NOT
evidence for C40 - it is reported, labelled "seen". The judges are, in order:
1. **DEV 2021-01 -> 2024-06** (the gate idea did not come from this period): all Protocol C DEV gates
   (>= 200 trades, PF >= 1.15, PF >= 1.0 at 2x costs, DD <= 35%, >= 3/4 periods positive, twin >= p95,
   top coin <= 20%) AND mechanism check: in DEV, plain C32 trades entered while BTC 20d return > 0
   have a LOWER PF than those entered while it is <= 0.
2. **RECENT 2026-03-26 -> 2026-09-25** (scored once by F18, never by any C family; one look):
   PF > 1.0 and profit after costs.
3. Walk-forward 8 half-years 2022H2 -> 2026H1: reported (contains the seen VALID period).
Decision: 1 and 2 pass -> forward paper test (>= 60 days or 100 trades, live public data) with MajorsTrend
running alongside. Anything fails -> KILL, not iterated on these periods.
Runner: `quant/run_c40.py`, output `runs/C40_trend_gate.json`.

### C40 result (2026-10-06) — KILL per fixed rule (`runs/C40_trend_gate.json`)
| Window | C32 PF / 300 → | C40 PF / 300 → | C40 DD | C40 twins |
|---|---|---|---|---|
| DEV 2021-01 → 2024-06 | 1.155 / 393 | 1.406 / 315 (112 trades) | 2.7% | p100 |
| VALID (seen) | 0.940 / 278 | 0.893 / 288 | 7.9% | p40 |
| RECENT 2026-03-26 → 09-25 | 0.852 / 261 | 0.758 / 271 | 11.1% | p13 |
DEV: every gate passed except ≥ 200 trades (112); the mechanism check passed in DEV (C32 per-trade PF 1.17 BTC-up vs
1.70 BTC-down). RECENT: PF 0.76, loss → KILL. Walk-forward 4/8 half-years positive.
**Diagnosis: the regime story was wrong after 2024.** In VALID and RECENT the relation REVERSES: C32 trades opened while
BTC was falling did worse (VALID 0.93 vs 1.20 BTC-up; RECENT 0.76 vs 0.94). 2025H1 and 2026Q2 losses came from shorting
crowded coins during BTC weakness (short squeezes), not from rallies. Funding crowding has now failed three ways
(C32 VALID, C39 OI gate, C40 trend gate): the 2021-24 edge has not held since 2024-H2 in any regime. Not iterated further.

## G1 = GridDCA (DeepSeek QuantBot grid + safety orders) — registered 2026-10-11, before any run
Strategy `bots/strategies/GridDCA.py` (entry-parameter fix 3a01fe7), run by the old bot's backtester (not
`eval_c`: the ladder / whole-stack exit needs the old bot's position-adjust hook). Two presets, judged separately,
settings exactly as committed in `bots/presets/` (no tuning, no variant chosen afterwards):
- **G1a `grid-dca-lowmin`** SOL/XRP/ADA/AVAX, 4 slots, stop −18%, 3 SO, target 2.5%, RSI 30, EMA200, cooldown 240.
- **G1b `grid-dca-majors`** BTC/ETH, 2 slots, stop −20%, 4 SO, target 2.0%, RSI 30, EMA200, cooldown 360.
Common: 5m futures, long only, 1x isolated, 300 USDT, tradable_balance_ratio 0.6, old-bot funding from history.

Seen window: 2025-05-07 → 2026-09-19 (DeepSeek's 6-variant sweep picked v4 there) — reported only, labelled "seen".
**Judge = UNSEEN 2021-01-01 → 2025-05-06**, one run per preset per cost level, no change afterwards.
Costs: base = fee 0.10% per side (Protocol C fee 0.05% + slippage 0.05%); 2x = 0.20% per side.
Gates (Protocol C DEV, adapted): ≥ 200 trades · PF ≥ 1.15 at base · PF ≥ 1.00 at 2x · max DD ≤ 35% ·
≥ 3 of 4 periods positive (2021, 2022, 2023, 2024-01-01 → 2025-05-06; by trade close date, base costs).
Deviations, stated now: no random-entry twins (no twin harness in the old backtester) and no top-coin gate (2–4 coins).
Decision: all gates pass → 14 days of paper (verdict 2026-10-26; Protocol C's 60 days / 100 trades still apply
before any live talk). Any gate fails → that preset and its paper bot are deleted. Not iterated.

## G2 = G1 + BTC trend filter (Michael, 2026-10-11) — registered before any G1 or G2 unseen result was seen
Idea: G1's seen-window losses came from starting ladders while the market fell for weeks (25 stops −94.70 vs
208 targets +83.01 USDT, market −45%). Filter = the live MajorsTrend BTC rule, unchanged: a NEW ladder (base order)
may open only while BTC's 20-day return at the last completed UTC daily close is > 0 (BTC/USDT:USDT 1d futures,
informative-timeframe merge, no lookahead). Safety orders, target and stop of an open ladder are not affected.
One setting: 20 days, no other lookback, no ETH/BNB variant. Everything else exactly as G1a / G1b.
Same windows, costs, gates, deviations and decision rule as G1. Honesty note: the idea was motivated by the SEEN
window, so the seen result is not evidence; the judge is the UNSEEN window, then forward paper trading.

### G1 result (2026-10-11) — both FAIL, per fixed rule (`runs/G1_griddca.json`, runner `quant/run_g1.py`)
| Preset | Window | 300 → | PF | PF 2x | DD | Trades | Win | Market |
|---|---|---|---|---|---|---|---|---|
| G1a lowmin | UNSEEN 2021-01 → 2025-05-06 | 159.96 | 0.71 | 0.70 | 52.2% | 817 | 88.9% | +2,827% |
| G1a lowmin | seen | 288.33 | 0.88 | 0.81 | 10.2% | 235 | 88.9% | −45% |
| G1b majors | UNSEEN | 236.00 | 0.82 | 0.78 | 31.1% | 350 | 90.0% | +190% |
| G1b majors | seen | 319.82 | 1.28 | 1.18 | 10.4% | 84 | 94.0% | +13% |
UNSEEN periods (2021 / 2022 / 2023 / 2024-25, USDT): G1a −7.2 / −100.5 / +18.6 / −51.0; G1b +9.4 / −63.6 / +17.3 / −27.0.
Gates failed: G1a PF, PF 2x, DD, periods; G1b PF, PF 2x, periods (passed trades and DD).
Diagnosis: the classic grid profile. ~89–90% of exits hit the small target (G1a 726 targets +346.37), but the
stop on a full ladder (G1a 88 stops −483.05; G1b 35 stops −353.23) more than erases it. It lost even in the
2021 bull market (alts up 28x): ladders bought every dip, and the dips that kept falling hit −18%/−20% on the
whole stack. 2022 (bear) was the worst year for both. G1b's positive seen result (+6.6%) does not transfer.
The seen-window run reproduces DeepSeek's v4 closely (235 vs 237 trades, −3.9% vs −2.4%; protections on here).
Action: both paper bots stopped 2026-10-11. Preset files kept only until G2 (which reuses their settings) is scored.

### G2 result (2026-10-11) — both FAIL (`runs/G2_griddca_trend.json`)
| Preset | Window | 300 → | PF | PF 2x | DD | Trades | Win |
|---|---|---|---|---|---|---|---|
| G2a lowmin + BTC filter | UNSEEN | 194.80 | 0.66 | 0.64 | 38.6% | 478 | 88.1% |
| G2a | seen | 286.71 | 0.78 | 0.70 | 9.6% | 131 | 87.8% |
| G2b majors + BTC filter | UNSEEN | 218.60 | 0.70 | 0.67 | 33.9% | 228 | 88.2% |
| G2b | seen | 302.19 | 1.04 | 0.97 | 11.8% | 59 | 93.2% |
UNSEEN periods (USDT): G2a +11.0 / −82.0 / +14.1 / −48.3; G2b −3.0 / −60.6 / +11.3 / −29.1.
Diagnosis: the filter did what it was built for (≈ 40% fewer ladders, smaller loss for G2a: −35% vs −47%), but it
made each trade WORSE (PF 0.71 → 0.66, 0.82 → 0.70): the losses were not only in falling markets. 2022 still lost
−82 / −61 — bear-market relief rallies switch the 20-day rule on and the ladders start right before the next leg
down. With the filter, wins still cover ~2/3 of the stop losses (G2a 420 targets +202.30 vs 55 stops −304.40).
The structure (many small wins vs a whole-stack stop) is the problem, not the timing.
Action (registered rule): grid presets and GridDCA / GridDCATrend deleted from bots/ (kept in git history). Not iterated.
Trial counter: +10 (DeepSeek's 6-variant sweep, G1 ×2, G2 ×2) → project raw 8,663 / unique 8,606.

## Batch 6 (registered 2026-10-13, before running) — momentum break of support/resistance (15m "snipe")
Michael's requested scalping idea: momentum trading at support & resistance on the 15m, quick snipe entries.
| ID | Rule | Exit |
|---|---|---|
| C41 | Level = the most recent CONFIRMED swing high/low (bar high above / low below the 2 bars before AND after it; usable 2 bars after it forms, no lookahead). A bar closes beyond the level AND its range (high−low) ≥ 1.5× the prior 20-bar average range → long above resistance / short below support | 1.5 / 3 ATR, 8 bars (2h) |

One setting, no grid. Universe = the 30 desk coins, 15m (2024-09 → 2026-09). Judged by the Protocol C DEV gates
on Q1-Q4 (2024-09-01 → 2025-09-01); VALID (2025-09 → 2026-03-26) only if DEV passes. Stated risk up front:
15m/30m families died on costs in batches 1-5 with swing exits (2/4 ATR, 1-2 day holds); this tests whether the
tight snipe exits (1.5/3 ATR, 8-bar cap) clear the 0.2% round trip where the swing exits did not. Runner:
`quant/gen_c.py 15m --batch BATCH6` + `quant/eval_c.py dev --batch BATCH6`.

Status 2026-10-14: NOT RUN. Registration kept; the 10-13 fresh search (research/fresh) took over. Run as registered if picked up again.

### C41 result (2026-10-17) — FAIL DEV (run exactly as registered, nothing changed)
| | value | gate |
|---|---|---|
| Book trades (20 slots, 300 USDT) | 9,347 of 39,555 signals | ≥ 200 ✔ |
| PF | 0.71 | ≥ 1.15 ✘ |
| PF at 2x costs | 0.51 | ≥ 1.0 ✘ |
| Max DD | 67.9% (300 → 99.6) | ≤ 35% ✘ |
| Quarters positive | 0 of 4 (Q1 −149, Q2 −51, Q3/Q4 0: book too small for min order, no trades) | ≥ 3 ✘ |
| Random twins beaten | 0.1% | ≥ 95% ✘ |
| Long / short PF | 0.75 / 0.67 | — |

All signals, before costs: PF 0.97 (avg −0.02%/trade); after costs −0.22%/trade. Exits: stop 43%, time 41%, target 16%.
Diagnosis: no edge even before costs (no quarter above gross PF 1.05), and the 0.2% round trip on a ~1-ATR 15m move turns
"nothing" into a steady loss. Same outcome as 15m batches 1-5; tight exits did not help. Not iterated.
Harness fix: `eval_c dev` skips timeframes with no trades (BATCH6 is 15m-only). Trial counter: quantlab raw 347 / unique 304,
project raw 8,677 / unique 8,620.

## Batch 7 (registered 2026-10-18, before any code or data run) — wick catcher (5m, maker) + sell the bounce (bear, 4h)
Michael's open focus (2026-10-18): "only the bear-market strategy and day trading (15m-1h) are failing". He picked
these two of five fresh ideas. One setting each, no grid, nothing re-tuned after a result is seen.

**Universe (deviation from PROTOCOL_C "Data", stated up front):** the 46 coins of the live bot's current whitelist
(`config_live_mainnet.json`, NFI46, 2026-10-18), Michael's fair-test framework of 2026-10-16: coins that trade now,
continuous history, no dead coins, no held-out coin sets. A coin enters when its data starts; PROTOCOL_C eligibility
(≥ 30 days listed, ≥ 10M USDT traded in the previous 24h) applies at every entry. BTC is used only for the market rule.
Book, gates, periods and twins: PROTOCOL_C unless a line below says otherwise.

| ID | Rule | Exit |
|---|---|---|
| C42 | **Wick catcher (long, 5m, maker).** Each 5m bar i, a resting limit BUY at L = close[i−1] × (1 − 3·σh), σh = std of the 288 previous 5m log returns × √12 (hourly σ, known before bar i opens). Filled only if the price trades THROUGH the limit: low[i] ≤ L × (1 − 0.001) (we are not first in the queue). Fill price = min(L, open[i]). One position per coin. | Take-profit = resting limit SELL at entry × (1 + 1.5·σh), filled only if high ≥ TP × (1 + 0.001). Stop = entry × (1 − 3·σh). Max hold 12 bars (1h) → market exit at that bar's close. |
| C43 | **Sell the bounce (short, bear only, 4h).** 4h bars built from 1h (UTC 00/04/08/12/16/20, completed bars only). At a 4h close: BTC is Bear (BTC 20-day return ≤ 0 at the last completed UTC daily close = `bullcalm_rule` Bull/Bear) AND the coin's own 20-day return < 0 (close vs 120 4h bars earlier) AND the previous 6 4h closes were all below the coin's 20-day average (SMA of 120 4h closes) AND this bar's high ≥ that average while it closes below it (rally into the average, rejected) → short at the next 1h open. | Stop 2 ATR, TP 3 ATR (ATR14 of the 4h bars at the signal), max hold 72 1h bars (3 days); stop / TP checked on 1h bars. |

**Execution and costs.**
- C42: maker fills (entry, TP) cost 0.02% per side, no slippage. Taker exits (stop, time) cost 0.05% fee + 0.05%
  slippage, the stop adds 0.05% extra; a bar opening below the stop fills at the open. "2x costs" doubles every cost.
  Entry bar (pessimistic, the order of the low and the fill inside the bar is unknown): if low[i] ≤ stop the trade is
  stopped in that bar; a TP cannot fill in the entry bar. Later bars: stop and TP both inside one bar → stop first.
  Real funding charged. A coin can fill again from the bar after an exit.
- C43: PROTOCOL_C costs unchanged (taker 0.05% + 0.05% per side, stop +0.05%, real funding).

**Data and periods.**
- C42: old-bot `data_nfi` 5m + funding (46 coins, 2024-02 → 2026-09; σh warm-up uses the first day).
  PROTOCOL_C intraday splits: DEV Q1–Q4 2024-09-01 → 2025-09-01, VALID Q5–Q6 2025-09-01 → 2026-03-26, walk-forward
  Q3–Q6 (3 of 4 positive). 2026-03-26 onward not used for selection.
- C43: old-bot `data` 1h + funding, same 46 coins, 2021-01 → 2026-03-25. PROTOCOL_C 1h splits:
  DEV 2021 / 2022 / 2023 / 2024H1, VALID 2024H2 → 2026-03-26, walk-forward 8 half-years.

**Gates.** PROTOCOL_C DEV / VALID / walk-forward, with two changes fixed now:
1. C42 "2x costs" = every cost above doubled (maker 0.04%, taker 0.10% + 0.10%, stop +0.10%).
2. C43 trades only in Bear markets, so years without a bear stretch have few or no trades. For C43 a period counts
   only if it has ≥ 10 book trades; the period gate = positive in ≥ 75% of counted periods with at least 2 counted
   (DEV), and ≥ 5/8 of counted half-years with at least 3 counted (walk-forward). A period that is not counted is
   reported, never treated as positive.

**Random twins (2,000).**
- C42: same coin, same holding length, entry at the open of a random 5m bar in the same period, same costs as C42
  (maker entry). Tests whether the WICK timing matters versus buying at any random moment with a limit order.
- C43: same coin, short, same holding, entry at a random 1h bar inside a BTC-Bear stretch only (fair to a bear-only
  rule: random shorts in bull markets would be too easy to beat).

**Reported, not gated:** results by market cell (Bull/Bear × Calm/Wild, `bullcalm_rule`), long-term stats, all-signal
PF before costs. Stated risk up front: C42 is the cost question (maker fills ~0.04% round trip instead of 0.20%) plus
adverse selection (limit buys fill most when the fall continues); C43 is the bear question (short edges since 2021 sat
mostly in 2022). Runner: `quant/run_c42_c43.py dev|valid|wf C42|C43`. Trial counter +2.

### Batch 7 results (2026-10-18) — C42 FAIL DEV, C43 FAIL DEV (run exactly as registered, nothing changed)
| | C42 wick catcher (5m, maker) | C43 sell the bounce (bear, 4h) | gate |
|---|---|---|---|
| Book trades (20 slots, 300 USDT) | 477 of 701 fills | 502 of 510 signals | ≥ 200 |
| Final / PF | 267.3 / 0.65 ✘ | 318.3 / 1.08 ✘ | PF ≥ 1.15 |
| PF at 2x costs | 0.60 ✘ | 1.005 ✔ | ≥ 1.0 |
| Max DD | 12.4% ✔ | 14.0% ✔ | ≤ 35% |
| Periods | Q1 −0.9, Q2 −22.3, Q3 +2.2, Q4 −11.7 → 1 of 4 ✘ | 2021 +38.6, 2022 −7.1, 2023 −20.7, 2024H1 +8.8 → 2 of 4 counted ✘ | C42 ≥ 3/4; C43 ≥ 75% of counted |
| Random twins beaten | 0.0% ✘ | 90.4% ✘ | ≥ 95% |
| Top coin share | 23.7% ✘ | 10.4% ✔ | ≤ 20% |
| All signals before costs | gross PF 0.72, avg −0.37% | gross PF 1.17, avg +0.45% | — |
| By market cell (book) | Bull-Calm PF 0.59 (322 tr), Bear-Calm 0.76, Bear-Wild 0.72, Bull-Wild 2.00 (27 tr) | Bear-Wild PF 1.07 (167), Bear-Calm 0.81 (257), 2021 before the cell median exists +34.8 | reported |

**C42 diagnosis.** Before costs it already loses (gross PF 0.72), so cheaper maker fees cannot rescue it as run. The
result hinges on the order of prices INSIDE the 5m bar that fills the order: 127 of 246 stops are the registered
pessimistic entry-bar rule (low of the fill bar ≤ stop → stopped). Without those trades gross PF would be 1.42, but that
assumes the opposite extreme; 5m candles cannot tell which is true — only 1m (or trade) data can. Fills cluster on
market-wide news bars (up to 43 of 46 coins in the same bar, e.g. 12:30 UTC US data releases), so the "wick" is often
a news move, not a liquidation flush. Bull-Calm (the most common cell) is the worst.
**C43 diagnosis.** Small edge before costs (gross PF 1.17) that survives 2x costs at break-even, low DD, profit spread
across coins — but it did NOT earn in the 2022 bear (−7.1 on 200 trades) and lost in 2023; the profit sits in 2021.
Bear-Calm (the cell it is meant for) PF 0.81; Bear-Wild 1.07. Twins 90%: not clearly better than random bear shorts.
Not iterated. Trial counter: quantlab raw 349 / unique 306, project raw 8,679 / unique 8,622.
Open option (NOT run, needs Michael's yes and a new registration as its own trial): replay C42's identical rule on 1m
data to resolve the entry-bar order — an execution-precision question, not a rule change.

## C42-1m (registered 2026-10-18, AFTER the C42 result, before any 1m data was downloaded) — same rule, 1m execution
Why: the C42 verdict hinged on the order of prices inside the 5m fill bar (127 of 246 stops came from the registered
pessimistic fill-bar rule). Michael asked for the identical rule replayed on 1m data. Because this was decided after
seeing C42, it is its own trial (+1), not a correction of C42; C42's FAIL DEV stays on record.

**Unchanged from C42:** universe (46 live coins), σh and the limit price L (from 5m bars exactly as before), the 0.1%
"trade through" fill rule, TP = entry × (1 + 1.5σh) with the same 0.1% through rule, stop = entry × (1 − 3σh), costs
(maker 0.02%, taker 0.05% + 0.05%, stop +0.05%, 2x doubles all), funding, one position per coin, eligibility, book,
DEV period Q1–Q4 2024-09-01 → 2025-09-01, all DEV gates, twins, cell report.
**Only change — execution resolved on 1m bars:**
- Fill: the first 1m bar inside the 5m bar whose low ≤ L × (1 − 0.001); fill price = min(L, that 1m bar's open).
- Exits checked on 1m bars from the fill minute on. Inside the fill MINUTE the pessimistic rule stays (low ≤ stop →
  stopped, no TP); later minutes: stop and TP in one minute → stop first; a minute opening below the stop fills at the open.
- Max hold unchanged in time: exit at the close of the 12th 5m bar counted from the fill bar (time exit).
- Data: Binance public futures 1m klines (data.binance.vision, USDT-M monthly files), only the windows around fills kept.
  Parity check before judging: in every used window the 1m lows/highs must reproduce the 5m low/high (mismatches
  reported; a 5m bar without matching 1m data is skipped, never guessed).
Runner: `quant/run_c42_c43.py dev C42M`. VALID / walk-forward only after a DEV pass (1m data for those periods is
downloaded only then).

### C42-1m result (2026-10-18) — FAIL DEV (run exactly as registered)
1m data: 46 of 46 coins, 704 fills used, 0 skipped (parity: every 1m window reproduced the 5m low/high exactly).
Book 300 → 290.0 (PF 0.87, x2 0.79, DD 6.6%), quarters Q1 +0.7 / Q2 −6.2 / Q3 +2.5 / Q4 −7.0 → 2 of 4 ✘, twins 0.0% ✘,
top coin 14.9% ✔. All fills before costs: gross PF 0.76, avg −0.32%; exits TP 388 / stop 243 / time 73.
Diagnosis: the 1m data settled the question. Stops in the fill minute fell from 127 (5m assumption) to 36; even with
all 36 removed, gross PF is 0.90 — 207 stops come in LATER minutes: after a 3σh wick the price usually keeps falling
another 3σh within the hour. Adverse selection is real, not an artefact of the 5m candles. By cell only Bull-Wild is
positive (27 trades). The wick-catcher idea in this form is closed. Trial counter +1.

## C44 wick follow (registered 2026-10-18, AFTER the C42 / C42-1m results, before any C44 code or VALID 1m data)
Idea from the C42-1m diagnosis: after a 3σh drop inside one 5m bar, price usually keeps falling within the hour
(207 of 704 wick buys stopped out in later minutes). C44 trades that continuation: SHORT the wick. Michael 2026-10-18:
"how are we going to make use of this" → go.

**Honesty rule:** the idea was formed on the DEV year (2024-09 → 2025-09), so DEV is in-sample and is REPORTED ONLY,
never used as a pass. The judge is the VALID period 2025-09-01 → 2026-03-26, never used to judge any C42 variant.

**Rule (46 live coins, eligibility, σh, L exactly as C42):**
- Trigger: each 5m bar i, a sell-STOP at L = close[i−1] × (1 − 3σh). Resolved on 1m: the first minute of bar i whose
  low ≤ L triggers it. Fill price = min(L, that minute's open) × (1 − 0.0005) (taker, slippage 0.05%).
- Take-profit: resting limit buy at entry × (1 − 3σh) (maker), filled only if the low trades 0.1% through it.
- Stop: entry × (1 + 1.5σh), taker; a minute opening above the stop fills at the open.
- Fill minute: no TP (its low may come before the fill); stopped only if that minute CLOSES ≥ stop (then the stop was
  surely crossed after the fill). Later minutes: stop and TP in one minute → stop first.
- Max hold: close of the 12th 5m bar counted from the trigger bar (time exit, taker). One position per coin; the coin
  can trigger again from the 5m bar after the exit.
- Costs: taker 0.05% + 0.05% slippage per side, stop +0.05%, maker TP 0.02%; real funding; 2x doubles every cost.
  Book: PROTOCOL_C (300 USDT, 20 slots, ≤ 10 shorts, minimum orders).

**VALID gates (all needed):** ≥ 100 book trades · PF ≥ 1.10 · profit at base costs · profit at 2x costs ·
DD ≤ 40% · beats ≥ 95% of 2,000 random twins (same coin, short, same holding, random 5m bar in VALID, same costs) ·
both VALID quarters (Q5, Q6) positive. Pass → forward paper test on live data before any live talk (min 60 days or
100 trades). Fail → closed, not iterated. Reported: DEV (in-sample), market cells, gross PF, fill-minute stats.
1m data: data.binance.vision monthly 1m, windows around triggers only, parity-checked against 5m as in C42-1m.
Runner: `quant/run_c42_c43.py c44`. Trial counter +1.

### C44 result (2026-10-18) — FAIL VALID (run exactly as registered)
1m parity: VALID 988 / DEV 790 triggers used, 0 skipped.
| | VALID (judge) | DEV (in-sample, report only) |
|---|---|---|
| Book (300 USDT, ≤ 10 shorts) | 290.1, PF 0.89 ✘, x2 273.6 ✘, DD 9.8% ✔, 569 trades ✔ | 263.0, PF 0.58 |
| Quarters | Q5 +13.3, Q6 −23.2 ✘ | all 4 negative |
| Random twins | 100% ✔ | 96.2% |
| All triggers | gross PF 1.41, net per trade +0.14% | gross PF 1.03 |
| By cell (book) | Bull-Calm PF 1.58, Bear-Wild 0.48, Bear-Calm 0.79, Bull-Wild 0.19 | all cells < 1 |
Diagnosis: the all-trigger profit is ONE day — 2025-10-10 (the big liquidation crash, 133 triggers, +456% summed per
trade); without the 3 best days the triggers lose (PF 0.46). The book can hold only 10 shorts, so on that day it caught a
small part of it and lost on the ordinary days. Shorting the wick does not repeat; flipping C42 does not mirror it either
(DEV gross PF 1.03, not 1/0.76, because stop/TP are asymmetric and the sell-stop triggers on a touch). Closed, not
iterated. Trial counter (C44 added as a one-off in quant/trials.py): see runs/trials.json.

## C45 Power of 3 — London sweep fade (registered 2026-10-18, before any code or run)
Michael's idea ("3 hours theory": Asia / London / New York sessions behave differently). ICT "Power of 3": Asia
accumulates, London fakes a move out of the Asia range, New York delivers the real move the other way. Not the same as
C10/C13 (they traded the FIRST break of the Asia range in its own direction and failed); C45 trades AGAINST a London break
that failed back into the range. One setting, no grid, nothing re-tuned after a result.

**Rule (1h bars, times fixed in UTC all year, no daylight-saving shift):**
- Asia range: high / low of the 7 bars opening 00:00 … 06:00 UTC.
- London sweep: among the bars opening 07:00, 08:00, 09:00, at least one high > Asia high (high sweep) or low < Asia
  low (low sweep) — exactly one side; both sides swept → no trade.
- Confirmation: the 09:00 bar (closes 10:00) closes strictly inside the Asia range.
- Trade: high sweep → SHORT, low sweep → LONG, at the open of the 10:00 bar. At most one trade per coin per day.
- Stop: the sweep extreme (highest high of 07–09 for a short, lowest low for a long). Target: the opposite side of the
  Asia range (Asia low for a short, Asia high for a long). No trade if the 10:00 open is already at/beyond the stop or
  the target.
- Time exit: close of the 19:00 bar (20:00 UTC, end of the New York session). Stop and target in one bar → stop first;
  a bar opening beyond the stop fills at the open.
- Costs PROTOCOL_C: 0.05% fee + 0.05% slippage per side, stop +0.05%, real funding; 2x doubles all.

**Universe / data:** the 46 live-bot coins (fair-test framework 2026-10-16), old-bot 1h futures + funding,
2021-01 → 2026-03-25; PROTOCOL_C eligibility at entry. **Periods / gates:** PROTOCOL_C 1h unchanged — DEV 2021 / 2022 /
2023 / 2024H1 (≥ 3 of 4 positive, PF ≥ 1.15, PF ≥ 1.0 at 2x, DD ≤ 35%, ≥ 200 trades, top coin ≤ 20%, twins ≥ 95%);
VALID 2024-07 → 2026-03-25 only after a DEV pass; walk-forward 8 half-years only after VALID.
**Twins (2,000):** same coin, same side, same holding length, entered at the 10:00 UTC open of a random day in DEV —
tests whether the London sweep matters versus simply trading at 10:00 in that direction.
**Reported, not gated:** long vs short, market cells (Bull/Bear × Calm/Wild), weekday vs weekend, exit mix.
Runner: `quant/run_c45.py dev|valid|wf`. Trial counter +1.

### C45 result (2026-10-18) — FAIL DEV (run exactly as registered)
| | value | gate |
|---|---|---|
| Book trades | 9,564 of 10,977 signals | ≥ 200 ✔ |
| Final / PF | 102.7 / 0.76 | PF ≥ 1.15 ✘ |
| PF at 2x costs | 0.61 | ≥ 1.0 ✘ |
| Max DD | 66.9% | ≤ 35% ✘ |
| Periods | 2021 −95.6, 2022 −41.8, 2023 −45.3, 2024H1 −14.5 → 0 of 4 | ≥ 3 ✘ |
| Random 10:00 twins beaten | 84.5% | ≥ 95% ✘ |
| Top coin share | 44% | ≤ 20% ✘ |
All signals before costs: gross PF 0.994, avg −0.005% per trade — no edge at all; the 0.2% round trip makes it a steady
loss. Long 0.79 / short 0.79, weekday 0.79 / weekend 0.78, every market cell below 1 (best Bear-Wild 0.88). Exits:
stop 58%, target 28%, time 14%: after a London sweep back into the range, price takes out the sweep extreme more often
than it reaches the far side of the Asia range. The sweep pattern is real on charts but carries no direction on these
46 coins. Closed, not iterated. Trial counter +1.

## C46 Coinbase premium (registered 2026-10-18, before any code or data download)
Idea: when US buyers on Coinbase pay more than Binance (premium up), US money is buying; when they pay less, US money is
selling. A market-wide flow signal from OUTSIDE Binance prices — a new kind of input for this lab. Free public data
(Coinbase Exchange + Binance spot). One setting, no grid, nothing re-tuned after a result. Trades both sides.

**Premium (each 1h bar, known at its close):** p = CB / (BN × U) − 1, with CB = Coinbase BTC-USD close, BN = Binance SPOT
BTCUSDT close, U = Coinbase USDT-USD close (corrects USDT drifting from $1, e.g. 0.988 in May 2022). Where U is missing
(USDT-USD not yet listed, early 2021) U = 1.0. Any input missing for that hour → no premium that hour.
- p4 = mean of the last 4 hourly premiums (all 4 needed). z = (p4 − mean of p4 over the previous 720 bars) / std of p4
  over the previous 720 bars (30 days, needs ≥ 600 values; the current bar is not in its own baseline).
- LONG signal: z crosses ≥ +2 (previous bar < +2). SHORT signal: z crosses ≤ −2 (previous bar > −2).
- Re-arm: after a long signal the next long needs z to have gone back below +1 first; shorts likewise above −1.

**Trade:** the signal is market-wide, so at each signal enter the 10 eligible coins of the 46 live-bot coins with the
highest quote volume over the previous 24h, at the next 1h open. Exit PROTOCOL_C style: stop 2 ATR, target 3 ATR
(ATR14 of the coin's 1h bars at the signal), max hold 24 bars. One position per coin (a coin already in a trade is
skipped). PROTOCOL_C costs (0.05% + 0.05% per side, stop +0.05%, real funding; 2x doubles).

**Universe / data:** 46 live-bot coins (fair-test framework), old-bot 1h futures + funding, 2021-01 → 2026-03-25;
Coinbase Exchange public candles BTC-USD and USDT-USD (1h); Binance public spot klines BTCUSDT (1h).
**Periods / gates:** PROTOCOL_C 1h unchanged — DEV 2021 / 2022 / 2023 / 2024H1 (≥ 200 book trades, PF ≥ 1.15, PF ≥ 1.0
at 2x, DD ≤ 35%, ≥ 3 of 4 positive, top coin ≤ 20%, twins ≥ 95%); VALID 2024-07 → 2026-03-25 only after a DEV pass;
walk-forward 8 half-years only after VALID.
**Twins (2,000):** same coin, side and holding, entered at a random 1h open in DEV.
**Reported, not gated:** number of signals per year by side, long vs short, market cells, premium data coverage.
Runner: `quant/run_c46.py dev|valid|wf`. Trial counter +1.

### C46 result (2026-10-18) — FAIL DEV (run exactly as registered)
Data: 46,584 hours, premium computed for 46,555 (Coinbase missing 8 h, Binance 19 h, USDT-USD 10 h after listing;
3,697 h before USDT-USD was listed set to 1.0 as registered). Premium median +0.005%, 1st–99th percentile −0.06% … +0.15%.
Signals per year ~100–150 (long and short about equal).
| | value | gate |
|---|---|---|
| Book trades | 3,594 | ≥ 200 ✔ |
| Final / PF | 208.3 / 0.90 | ≥ 1.15 ✘ |
| PF at 2x costs | 0.81 | ≥ 1.0 ✘ |
| Max DD | 45.2% | ≤ 35% ✘ |
| Periods | 2021 −68.4, 2022 −16.1, 2023 −41.4, 2024H1 +34.2 → 1 of 4 | ≥ 3 ✘ |
| Twins beaten | 70.3% | ≥ 95% ✘ |
| Top coin share | 36% | ≤ 20% ✘ |
All signals before costs: gross PF 1.016, avg +0.03% — no edge in either direction (long 0.86, short 0.94 after costs);
cells: Bull-Wild 1.21 and Bear-Wild 1.06 small positives, Calm cells < 1. A sharp move of the Coinbase premium carries
no usable direction for the next 24 h on these coins at 1h. Closed, not iterated (the opposite / fade reading is not
tested: before costs the follow version is ~0, so a fade is ~0 too). Trial counter +1.

## C47 BTC leads alts (registered 2026-10-18, before any code or data download)
Idea: when BTC jumps sharply within minutes, many alts follow a few minutes later. Buy (or short) the alts that have
NOT moved yet and hold briefly. Free Binance 1m data. One setting, no grid, nothing re-tuned after a result.

**Trigger (BTC, 1m futures bars, decided at a minute's close):** r5 = BTC close / close 5 minutes earlier − 1;
σ5 = std of BTC 1m log returns over the previous 1,440 minutes × √5. UP trigger: r5 ≥ 3·σ5 AND r5 ≥ +0.5%.
DOWN trigger: r5 ≤ −3·σ5 AND r5 ≤ −0.5%. After a trigger, no new trigger in the same direction for 30 minutes.
**Laggards:** for each eligible live coin (46 live-bot coins minus BTC; PROTOCOL_C eligibility from its 5m data: ≥ 30
days listed, ≥ 10M USDT 24h volume), a5 = its return over the same 5 minutes; ratio = a5 / r5. Laggard = ratio < 0.5.
Take the 5 laggards with the LOWEST ratio (fewer if fewer qualify).
**Trade:** UP trigger → LONG the laggards; DOWN → SHORT. Entry at the next minute's open (taker). Exit: time exit at the
close of the 30th minute after entry; stop at 3·σ5 of the coin (its own 1m log-return std over the previous 1,440
minutes × √5) against the entry; a minute opening beyond the stop fills at the open. One position per coin.
**Costs:** PROTOCOL_C taker 0.05% fee + 0.05% slippage per side, stop +0.05%, funding by 8h events crossed; 2x doubles.
**Data:** data.binance.vision USDT-M monthly 1m klines. BTC full months; alts only the minutes −10 … +45 around each
trigger (parity: missing minutes → that coin is skipped for that trigger, never guessed).
**Periods / gates:** PROTOCOL_C intraday — DEV Q1–Q4 2024-09-01 → 2025-09-01 (≥ 200 book trades, PF ≥ 1.15, PF ≥ 1.0
at 2x, DD ≤ 35%, ≥ 3 of 4 quarters positive, top coin ≤ 20%, twins ≥ 95%); VALID Q5–Q6 2025-09-01 → 2026-03-26 only after
a DEV pass (1m data downloaded only then); book 300 USDT, 20 slots, ≤ 10 per direction.
**Twins (2,000) — tests whether "lagging" matters:** at every trigger, the same number of coins drawn at random from
all eligible coins with data (not only laggards), same side, same exit rules, same costs.
**Reported, not gated:** up vs down triggers, triggers per quarter, market cells, average catch-up of laggards.
Runner: `quant/run_c47.py dev|valid|wf`. Trial counter +1.

### C47 result (2026-10-18) — FAIL DEV (run exactly as registered)
Data: full 1m klines 2024-08 → 2025-08 for BTC + 46 live coins (A / POL / VIRTUAL from their listing). 1,154 BTC triggers
in DEV (584 up / 570 down; 917 with ≥ 1 laggard). Implementation note: coins processed one at a time to stay inside RAM;
the rule is unchanged.
| | value | gate |
|---|---|---|
| Book trades | 2,411 | ≥ 200 ✔ |
| Final / PF | 235.8 / 0.62 | ≥ 1.15 ✘ |
| PF at 2x costs | 0.38 | ≥ 1.0 ✘ |
| Max DD | 21.4% | ≤ 35% ✔ |
| Quarters | Q1 −33.4, Q2 −17.5, Q3 −8.2, Q4 −5.2 → 0 of 4 | ≥ 3 ✘ |
| Random-coin twins beaten | 100% | ≥ 95% ✔ |
Before costs: laggards +0.017% per trade vs random coins −0.021% at the same triggers — lagging DOES matter (twins
100%), but the catch-up worth catching is ~0.04% while a round trip costs 0.20%. Long and short both lose (−0.17% /
−0.24% per trade after costs); every cell below 1. The lead-lag effect is real and measurable, but it is a
sub-minute, sub-0.1% effect that only very low-cost, very fast traders can use. Closed, not iterated. Trial counter +1.

## C48 Meme crowd impulse (registered 2026-10-19, before any code or data download)
Idea (Michael): meme coins have no institutional ground — they move on pure crowd impulse. When the crowd arrives
(volume AND number of trades explode while price breaks out), ride the trend, and get out when the crowd leaves.
Meme moves are 10–50%, so costs matter far less than in the 15m–1h families that died on fees. Memes are their own
group: normal research lists exclude them; this strategy trades ONLY them. One setting, no grid, nothing re-tuned
after a result. Long only (the "short after the pump dies" mirror is a separate idea, not part of this test).

**Universe (fixed now, from the Quantlab Market tab top 250 on 2026-10-19, all TRADING):** DOGE, 1000PEPE, PUMP, TRUMP,
PENGU, FARTCOIN, 1000SHIB, WIF, 1000BONK, BOME, SPX, NEIRO, PNUT, 1000FLOKI, TURBO, PEOPLE, 1000RATS, GIGGLE, USELESS,
MUBARAK, ZEREBRO, TUT, 龙虾, 牛来, 币安人生 (25). Coins listed after a period simply have no trades in it (no dead coins).
**Data:** data.binance.vision USDT-M monthly 15m klines (quote volume and number of trades are in the kline) + monthly
funding rates; 2024-08 → 2026-03 (August 2024 only as warm-up).

**Signal (15m bar s, decided at its close):** all of
1. quote volume[s] ≥ 3 × mean quote volume of the previous 96 bars (24 h);
2. number of trades[s] ≥ 3 × mean number of trades of the previous 96 bars;
3. close[s] > highest high of the previous 96 bars (new 24 h high);
4. close[s] > open[s];
5. PROTOCOL_C eligibility at s: ≥ 30 days listed, ≥ 10M USDT traded over the previous 96 bars.
**Entry:** LONG at the open of bar s+1 (taker). If that open is at or below the low of bar s → no trade.
**Exits (first one hit):**
- Safety stop = low of the signal bar s.
- Trailing stop = (highest high since entry, bars before the current one) − 3 × ATR14 (15m, at bar s). The active
  stop is the higher of safety and trailing. A bar whose low touches it exits at the stop (at the open if it opened
  below), plus stop slippage.
- Crowd leaves: from the 4th bar after entry on, at a bar's close, if mean quote volume of the last 4 bars < the
  96-bar baseline mean of rule 1 → exit at the next open.
- Time: close of the 96th bar after entry (24 h).
One position per coin; signals while a coin is in a trade are ignored.
**Costs (memes are thin — higher slippage than PROTOCOL_C):** fee 0.05% + slippage 0.10% per side, stops +0.05% extra;
real funding by 8h events crossed; 2x doubles fee and slippage.
**Periods / gates:** PROTOCOL_C intraday — DEV Q1–Q4 2024-09-01 → 2025-09-01: ≥ 200 book trades, PF ≥ 1.15, PF ≥ 1.0 at
2x costs, DD ≤ 35%, ≥ 3 of 4 quarters positive, top coin ≤ 20% of profit, twins ≥ 95%. VALID Q5–Q6 2025-09-01 →
2026-03-26 only after a DEV pass; walk-forward only after VALID. Book 300 USDT, 20 slots (stake equity/20), ≤ 10 longs.
**Twins (2,000):** same coin, long, same holding (bars) and cost, entered at a random eligible 15m open of that coin in
the same split.
**Reported, not gated:** trades per coin and per quarter, exit reasons, late entries (share of trades whose high after
entry never got 1 ATR above the entry), PF without the 3 best days, market cells, average win / average loss.
Runner: `quant/run_c48.py dev|valid|wf`. Trial counter +1.

### C48 result (2026-10-19) — FAIL DEV (run exactly as registered)
Data: 15m klines + funding for 24 of 25 coins (牛来 listed 2026-08-30, no data in range; 龙虾 no signal); GIGGLE / USELESS /
币安人生 listed after DEV, so 20 coins traded in DEV.
| | value | gate |
|---|---|---|
| Book trades | 1,444 | ≥ 200 ✔ |
| Final / PF | 276.3 / 0.91 | ≥ 1.15 ✘ |
| PF at 2x costs | 0.71 | ≥ 1.0 ✘ |
| Max DD | 10.9% | ≤ 35% ✔ |
| Quarters | Q1 −4.3, Q2 −10.3, Q3 +2.7, Q4 −11.8 → 1 of 4 | ≥ 3 ✘ |
| Random twins beaten | 100% | ≥ 95% ✔ |
| Top coin share | 37% (PNUT) | ≤ 20% ✘ |
Before costs the crowd signal is REAL: gross PF 1.21, +0.23% per trade, and it beats all 2,000 random entries on the
same coins. After the registered meme costs (0.30% round trip) it is −0.08% per trade. Moves caught are small, not
10–50%: average win +3.6%, average loss −2.0%, median hold 6 bars (1.5 h), 36% late entries (price never got 1 ATR
above the entry); exits trail 735 / stop 475 / fade 260. Coin split: smaller memes positive (PNUT 1.76, PENGU 1.40,
WIF 1.31, ZEREBRO 1.37, FLOKI, NEIRO, TRUMP), the biggest / most liquid ones lose (DOGE 0.61, 1000SHIB 0.66, 1000PEPE
0.77, FARTCOIN 0.56). Cells: Bear-Calm 1.31 and Bull-Wild 1.17 positive, Bull-Calm 0.72 worst. PF without the 3 best
days 0.84. Closed as registered, not re-tuned. Trial counter +1.

## C49 Meme crowd impulse, 1h (registered 2026-10-20, AFTER the C48 result, before any C49 code or run)
Why: C48 (15m) had a real pre-cost edge (gross PF 1.21, twins 100%) but caught small moves (avg win +3.6%, median hold
1.5 h) so the 0.30% meme round trip ate it. Same crowd rule on 1h bars: wider stops, bigger moves per trade, costs a
smaller share. One setting, no grid, nothing re-tuned after a result. Long only.
**Universe / data / costs:** identical to C48 (same 25 memes; 1h bars built from the cached C48 15m klines: open first,
high max, low min, close last, quote volume and number of trades summed; an hour with any 15m bar missing = missing).
**Signal (1h bar s):** quote volume ≥ 3 × mean of the previous 24 bars; number of trades ≥ 3 × mean of the previous 24;
close > highest high of the previous 24 bars; close > open; PROTOCOL_C eligibility (≥ 30 days, ≥ 10M USDT over the
previous 24 bars).
**Entry / exits:** LONG at the next 1h open (no trade if it opens at/below the signal-bar low). Safety stop = signal-bar
low; trailing stop = highest high since entry (earlier bars) − 3 × ATR14 (1h, at s); crowd leaves = from the 4th bar on,
mean quote volume of the last 4 bars < the 24-bar baseline → exit next open; time exit at the close of the 72nd bar
(3 days). One position per coin. Costs: fee 0.05% + slippage 0.10% per side, stops +0.05%, real funding; 2x doubles.
**Periods / gates / twins / reported:** identical to C48 (DEV Q1–Q4 2024-09-01 → 2025-09-01, PROTOCOL_C intraday gates,
VALID only after a DEV pass, 2,000 same-coin random-entry twins, book 300 USDT / 20 slots / ≤ 10 longs).
Runner: `quant/run_c49.py dev|valid`. Trial counter +1.

### C49 result (2026-10-20) — FAIL DEV (run exactly as registered)
| | value | gate |
|---|---|---|
| Book trades | 527 | ≥ 200 ✔ |
| Final / PF | 293.0 / 0.96 | ≥ 1.15 ✘ |
| PF at 2x costs | 0.83 | ≥ 1.0 ✘ |
| Max DD | 11.3% | ≤ 35% ✔ |
| Quarters | Q1 +10.8, Q2 −16.9, Q3 +2.9, Q4 −3.8 → 2 of 4 | ≥ 3 ✘ |
| Random twins beaten | 92.3% | ≥ 95% ✘ |
| Top coin share | 31% | ≤ 20% ✘ |
1h made the moves bigger (avg win +6.1%, avg loss −3.6%) but the pre-cost edge got smaller (gross PF 1.15, +0.31% per
trade vs costs ~0.31%): net −0.005% per trade = break-even. PF without the 3 best days 0.75. The best coins changed
completely from C48 (15m best PNUT 1.76 → 1h 0.94; 1h best WIF 2.75, PENGU 2.37, BONK 1.57, DOGE 1.34), so per-coin
differences are noise, not a stable "small memes" pattern. Cells: Bull-Wild 1.17, Bear-Calm 1.10, Bear-Wild 0.39.
Conclusion over C48 + C49: the meme crowd impulse is real before costs (15m and 1h) but about the size of meme trading
costs; long-only breakout-follow does not clear them. Closed, not re-tuned. Trial counter +1.

## C50 Meme crowd impulse 1h, strong surges only (registered 2026-10-20, AFTER the C48 / C49 results, before any C50 run)
Michael: fewer, more selective entries. Identical to C49 in every way except rules 1–2 of the signal: quote volume
≥ **6 ×** and number of trades ≥ **6 ×** their previous-24-bar means (C49: 3 ×). One setting, chosen before any run, not
re-tuned. Because C48 / C49 DEV results were seen before this was written, DEV is partly seen: C50 counts as a pass only
if it passes DEV AND then VALID (Q5–Q6 2025-09-01 → 2026-03-26, no meme test has looked at it), same PROTOCOL_C gates.
Runner: `quant/run_c50.py dev|valid`. Trial counter +1.

### C50 result (2026-10-20) — FAIL DEV (run exactly as registered; fails 2 of 7 gates)
| | value | gate |
|---|---|---|
| Book trades | 103 | ≥ 200 ✘ |
| Final / PF | 321.2 / 1.47 | ≥ 1.15 ✔ |
| PF at 2x costs | 1.33 | ≥ 1.0 ✔ |
| Max DD | 4.2% | ≤ 35% ✔ |
| Quarters | Q1 +3.1, Q2 −6.5, Q3 +21.3, Q4 +3.4 → 3 of 4 | ≥ 3 ✔ |
| Random twins beaten | 99.8% | ≥ 95% ✔ |
| Top coin share | 22.8% | ≤ 20% ✘ |
Strongest meme result so far: +1.48% per trade after costs (gross PF 1.70), avg win +10.7% / avg loss −4.5%, win rate 39%,
late entries 25% (C49 34%). Weak points: only ~100 trades a year on 20 coins, and PF without the 3 best days is 0.77 — the
profit leans on a few big days (2025-04-22, 05-08, 08-22). Cells: Bull-Wild 2.28, Bear-Calm 2.07, Bull-Calm 1.05,
Bear-Wild 0 (8 trades). 2x leverage: 300 → 342, DD 8.3%, 0 liquidations (reported only). Per registered rule: FAIL,
VALID not opened. Not re-tuned. Trial counter +1.

### C50 VALID opened by Michael's decision (2026-10-20, before the VALID run)
C50 failed DEV on 2 of 7 gates (103 < 200 trades, top coin 22.8% > 20%) while passing PF, 2x costs, DD, quarters and
twins. Michael decided to open VALID anyway (the failures are sample size). Recorded as a gate override: the C50 rule is
run unchanged on VALID Q5–Q6 (2025-09-01 → 2026-03-26) with the registered PROTOCOL_C VALID gates (PF ≥ 1.10, profit at
base and 2x costs, DD ≤ 40%). Reported also: DEV + VALID combined trades, top coin share, PF without the 3 best days.
The ledger row carries "override": "DEV fail, VALID opened by Michael 2026-10-20".

### C50 VALID result (2026-10-20, opened by override) — FAIL VALID
| | value | gate |
|---|---|---|
| Book trades | 83 | — |
| Final / PF | 302.6 / 1.07 | PF ≥ 1.10 ✘, profit ✔ |
| 2x costs | 298.2 / PF 0.95 | profit ✘ |
| Max DD | 3.5% | ≤ 40% ✔ |
| Q5 / Q6 | +7.5 / −5.0 | (reported) |
| Twins beaten | 87.5% | (reported) |
Still positive on unseen data (+0.22% per trade after costs, gross PF 1.19, avg win +7.5% / loss −4.8%, top coin 19%),
but much weaker than DEV (+1.48%) and not robust to double costs. PF without the 3 best days 0.76. Biggest loser: the
new coin 币安人生 (8 trades, −46% summed). Cells: Bear-Wild 1.35, Bull-Calm 0.53. DEV + VALID combined: 190 trades,
PF 1.33, +0.93% per trade. Verdict per gates: FAIL VALID. Michael asked for a paper forward test regardless
(information only, no live money) and a C51 test of the same rule on non-meme coins.

## C51 Crowd surge on non-meme coins (registered 2026-10-20, AFTER the C50 DEV/VALID results, before any C51 data or run)
Michael: a crowd surge is not only a meme thing; more coins = more trades and less dependence on one coin. The C50 rule
UNCHANGED (1h; quote volume and number of trades ≥ 6 × their previous-24-bar means; close above the 24-bar high; green
bar; PROTOCOL_C eligibility; long at the next open; safety stop signal-bar low; trail 3 × ATR14; fade from the 4th bar;
72-bar cap; fee 0.05% + slippage 0.10% per side, stops +0.05%, real funding; one position per coin), on a different coin
set: `runs/c51_coins.json` = the Quantlab Market tab top 250 by 24h volume on 2026-10-20 minus the 25 C48 memes, minus
MOODENG and 4 (memes), minus gold tokens PAXG / XAUT → 222 coins trading today (coins listed later simply start later).
**Data:** data.binance.vision USDT-M monthly 1h klines (quote volume, number of trades) + funding, 2024-08 → 2026-03.
**Periods / gates:** PROTOCOL_C intraday, DEV Q1–Q4 2024-09-01 → 2025-09-01 with all 7 gates (≥ 200 trades, PF ≥ 1.15,
PF ≥ 1.0 at 2x, DD ≤ 35%, ≥ 3 of 4 quarters, twins ≥ 95%, top coin ≤ 20%); VALID only after a DEV pass. Book 300 USDT,
20 slots, ≤ 10 longs. Twins: 2,000 same-coin random entries. Reported: trades per coin, BTC/ETH/large vs small
coins, late entries, PF without the 3 best days, market cells.
Runner: `quant/run_c51.py dev|valid`. Trial counter +1.

### C51 result (2026-10-20) — FAIL DEV (run exactly as registered)
| | value | gate |
|---|---|---|
| Book trades | 657 | ≥ 200 ✔ |
| Final / PF | 269.6 / 0.88 | ≥ 1.15 ✘ |
| PF at 2x costs | 0.77 | ≥ 1.0 ✘ |
| Max DD | 16.8% | ≤ 35% ✔ |
| Quarters | Q1 −24.8, Q2 −24.1, Q3 +28.0, Q4 −9.6 → 1 of 4 | ≥ 3 ✘ |
| Twins beaten | 97.3% | ≥ 95% ✔ |
| Top coin share | 7.7% | ≤ 20% ✔ |
154 coins traded, 63 positive. Gross PF 1.07 (+0.15% per trade before costs, −0.05% after; even at PROTOCOL_C's normal
0.05% slippage it stays below zero). Only Bear-Wild positive (PF 2.12, 49 trades). On non-meme coins the 6x crowd surge
carries a much smaller edge than on memes (C50 DEV gross PF 1.70): the surge effect is meme-specific. Closed. Trial +1.
Also (information, outside the research periods): the C50 forward code self-tested on 2026-08-20 → 10-20 (live klines)
gave 36 trades, −0.81% per trade, 300 → 295.6 — consistent with C50's edge fading after DEV (DEV +1.48%, VALID +0.22%).

## E1 E0V1EN live-readiness check (registered 2026-10-20, before any E1 data download or run)
Purpose (Michael): NFI is idle in this market (0 trades since 10-16 live, paper NFI none since 10-15); decide whether
E0V1EN can run next to it. E0V1EN = community strategy (the author's public strategy repo), unchanged since our download
2026-10-12 (bots/strategies/E0V1EN.py sha256 420bffe0…, + E0V1EN.json params); author's code frozen 2025-03-27, so
every period after that is out-of-sample for it. Longs only, 5m, 1x, 3 slots, market orders, stop −25% + trailing.
**Test A — last 3 months, the coins it would trade live:** the paper bot's 124-coin list minus memes (PUMP, TRUMP,
PENGU, SPX, USELESS, WIF, FARTCOIN, MELANIA; DOGE stays) minus HOOD (a stock perp) = 115 coins. old-bot backtest
with the paper preset unchanged (bots/presets/e0v1en.json via quant/run_ext.py config), fee 0.10% per side, 300 USDT,
2026-07-20 → 2026-10-20, run in 3 monthly chunks (07-20→08-20, 08-20→09-20, 09-20→10-20; each starts from 300, open
trades force-closed at a chunk end — memory limit).
**Test B — parity with the paper bot:** same backtest on the paper bot's full 124 coins for 2026-10-16 → 10-20; count
how many of the paper bot's closed trades in that window it reproduces (same coin, entry within ±15 minutes).
**Pass (all needed):** A total profit > 0 · A PF ≥ 1.20 · A worst drawdown inside any chunk ≤ 25% · ≥ 2 of 3 months
positive · B reproduces ≥ 70% of the paper trades.
**Reported, not gated:** trades per week, win rate, avg / worst trade, exit reasons, hours both E0V1EN and NFI would
hold positions (from the NFI paper record), 2026-10 alone.
Pass → a small live start next to NFI is proposed (Michael decides size and start). Fail → stays paper. Trial counter +1.

### E1 result (2026-10-20) — PASS (run exactly as registered)
Test A, 115 coins, fee 0.10% per side, each month from 300 USDT, 1x:
| Month | Trades | Profit | Max DD | Win rate | Worst trade |
|---|---|---|---|---|---|
| 07-20 → 08-20 | 152 | +171.9 (300 → 472) | 13.5% | 74% | −25.2% |
| 08-20 → 09-20 | 239 | +482.3 (300 → 782) | 8.3% | 78% | −25.2% |
| 09-20 → 10-20 | 191 | +106.8 (300 → 407) | 11.7% | 74% | −25.2% |
Total +761, PF 1.72, 582 trades (~44 / week), avg trade +0.93%, 13 stop-losses at −25%; exits mostly trailing stop
(293), cci_loss_sell 132, fastk_profit_sell 110. Test B: the backtest reproduces 8 of the paper bot's 10 closed trades
10-16 → 10-20 (80%). Gates: all 5 pass. Overlap with NFI not measurable (paper NFI record only since 10-12: 36 h,
16 h shared). Caveats: coin list is today's (fair-test framework), monthly chunks force-close open trades, the −25%
stop is the main tail risk (13 hits in 3 months). Next per registration: small live start next to NFI, Michael decides.
