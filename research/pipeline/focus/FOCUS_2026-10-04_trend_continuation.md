# Focused search: trend_continuation drawdown (pre-registered 2026-10-04)

**Written before any of these configurations was run.** Machine-readable copy: `trend_continuation_dd.yaml`.

## Why
Campaign 2026-10-04 (batches 4-13), candidate `d9ca7c18acee`
`trend_continuation · vol_expanding · both` (trend-only regime gate, structure stop, exit on the
opposite signal, 400-bar time exit) passed every gate up to G3 except portfolio drawdown:
PF 1.20 (1.135 at 2x costs), t 3.76, random-entry p100, 4/4 regimes, 79/133 coins, neighbours 4/4,
**10-slot drawdown 48.8% vs the 40% bar**. It never reached the out-of-sample coins.

## Question
Does a nearby configuration, or a different portfolio construction, bring drawdown within 40%
**and** does the edge survive the 280 coins no research has used?

## Grid (36 configurations, all fixed now)
| Dimension | Values |
|---|---|
| filters | `vol_expanding` (base) · `vol_expanding + btc_regime` · `vol_expanding + volume` |
| regime gate | all trends (base) · strong trends only |
| direction | both (base) · long only |
| stop | structure 2.0 x ATR (base) · ATR 3.0 · ATR 8.0 |
Fixed: trend_mode both, no take-profit, exit on the opposite signal, 400-bar time exit, leverage 1.

## Portfolio constructions (evaluated on every configuration)
- **P10**: 10 slots, stake = equity / 10 (the campaign's gate)
- **P20**: 20 slots, stake = equity / 20
- **LIVE**: 20 slots, at most 10 positions in the same direction (the live account's rules)

**G3 drawdown is judged on LIVE** (declared now). P10 and P20 are reported.

## Gates
Unchanged gates v1 (DSR recorded, not blocking), except the drawdown construction above.
Out-of-sample G4 on the 280 unseen coins and G5 (8 half-year folds) decide VALIDATED.
36 trials are added to the deflated-Sharpe count.

## Decision rule
- VALIDATED → eligible for a **paper** forward test (stage S5) only. Never live from this search.
- None validated → the lead is closed: recorded REJECTED with the reason; no wider re-search of
  this family on the same data.

---

## RESULT (run 2026-10-04 13:48-14:02 UTC, batches 14-16): no configuration validated. LEAD CLOSED.

| Stage | Out |
|---|---|
| G2 edge (development coins) | 19 of 36 |
| G3 robustness | 13 (drawdown on the live construction and/or regimes) |
| Diversity (near-copy of a better variant) | 1 |
| G4 out-of-sample (280 unseen coins) | **3 — all failed** |

The three that reached the unseen coins (all `both`, all-trend gate, structure stop; filters vol_expanding / +btc_regime / +volume):
- Development: PF 1.18-1.20, 4/4 regimes, live-construction drawdown 37.8-39.8% (passes; the 10-slot figure was 48.5-48.8%).
- **Unseen coins: PF 1.03-1.05 (bar 1.10); only 17-29% of the development expectancy kept (bar 60%); 113-121 of 280 coins profitable; recent 2025-26 negative; live-construction portfolio −61% to −73% with 74-83% drawdown.** G5 time folds passed 5/8. The edge measured on the development coins mostly does not transfer to coins no research has touched.

**Design error, recorded:** under `trend_mode: both` the engine's `btc_regime` filter applies no constraint (signals.py), so every `+btc_regime` configuration duplicated its plain twin: **24 distinct configurations, not 36**. The DSR trial count includes the 12 duplicates (conservative). The duplicate pairs' random-entry percentiles differ (94.5 vs 97.0) only by random seed, which shows that 200-replica check is noisy near the p95 bar.

**Decision (per the rule above):** the lead is closed. No wider re-search of `trend_continuation` on this data. Nothing goes to forward testing or live.
