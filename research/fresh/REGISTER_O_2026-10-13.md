# Batch O - open-interest positioning at 1h (slow, not latency), registered 2026-10-13 before any result

Michael: "work on a loop until you come up with a strategy". New data from batch S (user_data/oi_data: 5m OI from
the Binance metrics archive, point-in-time top-10 coins 2022-2026) used at 1h, holds 1-3 days, same frame as
FlowTrend so results compare directly: PIT top-10, fit 2022-2024 (setting chosen on the account), test
2025-01..2026-09-21, 0.10%/side + funding, 6 slots equity/6, 1x, stop k x normal daily move, one trade per coin
per side per 24h. zOI = z of the 24h log change of OI vs its 720h mean/sd. r10 = 10-day return, sigma = daily move.

| id | family | long rule (short = mirror) | grid |
|---|---|---|---|
| O1 | new money joins the trend | r10 > 0, 24h return > 0, zOI >= k | k [1.5,2], hold [24,48]h, stop 2 |
| O2 | trapped shorts in uptrend | r10 > 0, 24h return <= -1 sigma, zOI >= k (new shorts piled into the dip) | k [1.5,2], hold [24,48]h, stop 2 |
| O3 | deleveraged dip in uptrend | r10 > 0, 24h return <= -1 sigma, zOI <= -k (longs flushed, not new shorts) | k [1.5,2], hold [48,72]h, stop 3 |
| O4 | funding against the trend | r10 > 0 and 24h avg funding z <= -k vs its 30d (shorts paying while price trends up) | k [1.5,2], hold [48,72]h, stop 2 |
| O5 | flow + OI in trend | r10 > 0, taker buy-share z(24h) >= 1.5 and zOI >= k | k [1,1.5], hold 48h, stop 2 |

Pass bar (as batch G): TEST >= 30 trades, avg > 0, PF >= 1.2, 2025 and 2026 both positive, FIT avg > 0, test
account (6 slots) > 300, at least half the grid positive on test. Overlap with FlowTrend signals reported (a filter
of FlowTrend is not a new strategy). No unseen/held-out coin sets.
Running count of strategy families tried today (A, B, F, G, H, L, S): 37; this batch adds 5.

## Results (batch_o.py -> batch_o_results.json), 2026-10-13: none pass
| family | chosen | fit | test | test account | grid+ | overlap FlowTrend |
|---|---|---|---|---|---|---|
| O1 new money in trend | k2, 24h | -0.16% | -0.13% PF 0.93 | 263 | 0/4 | 40% |
| O2 trapped vs trend | k2, 24h | +0.26% (116) | -0.49% PF 0.77 | 284 | 0/4 | 26% |
| O3 deleveraged dip | k1.5, 48h | +0.78% acct 546 | -0.03% PF 0.98, 2026 -42 | 286 | 0/4 | 12% |
| O4 funding vs trend | k2, 72h | -0.13% | +0.16% PF 1.05 | 310 | 2/4 | 26% |
| O5 flow + OI in trend | k1 | +0.75% | +0.29% PF 1.13, 2026 -18 | 365 | 2/2 | 70% |
OI adds nothing at 1h; O5 is weaker than FlowTrend alone (OI confirmation removes good trades).
