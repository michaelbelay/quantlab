# Batch H - Bear-Rip Short v2, registered 2026-10-13 before any result

Michael passed in an outside review: B3 rip-in-downtrend short was rejected for losing in bull years, which is what a
bear specialist does. Proposal: trade it only in a sustained BTC downtrend, short only AFTER the relief rally fails,
and size by stop distance (5x only as margin efficiency, not exposure). Judge it on bear-regime profit and on staying
out of trouble elsewhere, not on bull-year profit.

Same frame as batch B: point-in-time top-10 coins by last month's traded value, 1h Binance futures, 0.10%/side +
funding, FIT 2022-01..2024-12 (setting chosen on the fit account), TEST 2025-01..2026-09-21. No unseen/held-out sets.

## Rules
- **Bear regime** (at the signal hour): BTC 20d return < 0 AND BTC close below its 50-day average.
- **Setup**: coin in this month's top-10, coin [10,20]d return < 0, 24h rise >= [1.5, 2, 2.5] x its normal daily move (sigma).
- **H0 baseline (B3, bear-gated)**: short next open, stop 3 sigma, exit [48,72]h. Same grid, same regime.
- **H1 Bear-Rip v2 (failed-rally confirmation)**: after the setup, follow the rally peak (highest high since the setup
  hour). Short at the next open after the first hourly close that is >= [0.5, 1.0] sigma below that peak, within 24h;
  otherwise no trade. Stop = peak x (1 + 0.5 sigma). Exit [48,72]h.
- One trade per coin per 24h.

## Account (300 USDT, leverage-aware)
- Isolated margin, 5x max, hard stop, no averaging down, **max 2 open shorts**.
- Size by stop: risk 1% of equity per trade -> notional = 0.01 x equity / stop distance; margin = notional / 5;
  total margin capped at equity (notional <= 5 x equity / 2 per position). Notional < 5 USDT -> skipped.
- Liquidation modelled: at 5x with ~1% maintenance margin a position dies at a ~19% adverse move. Stop distance >= 18%
  -> trade skipped. A loss can never exceed the position's margin.
- Secondary (reported, not used to choose): 2% risk per trade.

## Pass bar (H1)
TEST: >= 30 trades, avg > 0, PF >= 1.2, account (1% risk) > 300, account max drop <= 15%; FIT avg > 0; at least half of
the 24 settings positive on test; and H1 beats H0 on the test account (the confirmation must add something).
Bull/other periods: no trades by design - reported as such. Per-year numbers reported for both.

## Results (bear_rip.py -> bear_rip_results.json), 2026-10-13: H1 FAIL
Bear regime = 41% of hours 2022-26 (fit 39%, test 44%).
| | chosen on fit | fit | test | test account 1% risk | 2% risk | grid + on test |
|---|---|---|---|---|---|---|
| H0 B3 bear-gated | 2.0 sigma, 10d, 72h | 164 trades +0.29% | 84 trades +0.50% PF 1.17 | 300 -> 294, drop 5% | 287, drop 11% | 9/12 |
| H1 Bear-Rip v2 | 2.5 sigma, 20d, confirm 0.5, 48h | 98 trades **-0.28%** | 42 trades +0.96% PF 1.52 | 300 -> 300, drop 8% | 298, drop 15% | **7/24** |
Sum of % by year (H1): 2022 +43, 2023 -53, 2024 -18, 2025 +26, 2026 +14 (H0: +157, -101, -8, +35, +7).
- The failed-rally entry makes stops tighter (median 5.5% vs 13%) and the test trades better per trade, but fit is
  negative and only 7 of 24 settings are positive on test -> the test number is not robust.
- The BTC bear gate does not keep it out of trouble: 2023 and 2024 (bull years) still lose, because their pullbacks
  count as "bear" hours. The edge lives in 2022 (deep bear).
- Stop-distance sizing works as intended (drops 5-15%, nothing near liquidation, 0 skipped), but at 1-2% risk with
  2 positions the account barely moves either way.
