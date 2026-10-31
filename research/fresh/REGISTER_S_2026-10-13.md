# Batch S - shock-and-settle (forced positioning), registered 2026-10-13 before any OI data was looked at

Outside review passed in by Michael after the lead-lag rejection: a sharp 15-30 min move WITH open interest falling
= forced liquidation (longs flushed on a drop, shorts squeezed on a rise), not fresh positioning. Trade the settle:
enter after price starts to recover/give back, hold 1-4h. Two-sided, longs and shorts reported separately.

## Data (new here)
- Open interest: Binance USD-M "metrics" daily archives (data.binance.vision), 5-min sum_open_interest.
- Price: Binance USD-M 5m klines (monthly archives).
Only for coins in that month's point-in-time top-10 (by last month's traded value, same list as batch B) plus the
month before (warm-up). FIT 2022-01..2024-12 (setting chosen on the fit account), TEST 2025-01..2026-09-20.

## Rule (long; short = exact mirror)
- Shock: return over the last W min <= -k x sigma_W (sigma_W = sd of 5m log returns over the previous 30 days x sqrt(W/5)),
  AND open interest over the same W min falls by >= o %.
- Settle: within the next 60 min, the first 5m close that has recovered >= 25% of the shock (from the shock-start
  price down to the lowest low since the shock start). Enter at the next 5m open. No trade if it does not happen.
- Stop: lowest low since shock start minus 10% of the shock size. Target: entry + 2 x (entry - stop) (2R).
  Time exit after H min. Costs 0.10%/side. One trade per coin per 4h.
- Grid: W [15, 30] min, k [3, 4], o [1, 2] %, H [60, 240] min -> 16 settings.

## Account (same as batch H)
300 USDT, isolated 5x max, size by stop: 1% equity risk per trade (2% reported), notional capped at 5 x equity / 2,
max 2 open positions, stop distance >= 18% skipped (liquidation), loss never above margin.

## Pass bar
TEST: >= 30 trades, avg net > 0, PF >= 1.2, 2025 and 2026 both positive, account (1% risk) > 300; FIT avg > 0;
at least 8 of 16 settings positive on test. Longs and shorts reported separately (and either side alone may pass).

## Results (get_oi.py -> user_data/oi_data, 56 coins; shock.py -> shock_results.json), 2026-10-13: FAIL
- All 16 settings lose on fit AND on test, longs and shorts alike: test -0.20 .. -0.46% per trade net, i.e. about
  -0.05 .. -0.25% even before the 0.20% round-trip cost. 0/16 settings positive on test for both / long / short.
- Best on fit (30 min, 4 sigma, OI -2%, 1h): test 448 trades -0.20%, PF 0.79, 300 -> 210 at 1% risk (drop 33%).
  Every year 2022-2026 negative. Longs alone 0.72 PF, shorts alone 0.67 PF.
- Shocks with OI destruction do not bounce enough after the 25% recovery to pay: the move after entry is flat to
  slightly against. Typical stop only 2.3% away, so costs are a large part of each R.
