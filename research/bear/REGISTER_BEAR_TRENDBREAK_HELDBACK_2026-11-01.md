# Trend break short – held-back test (registered 2026-11-01, before opening 2026-04 → 2026-09)

Michael: "test it". Variant **T_ema480|h168|s6** from `REGISTER_BEAR_EXPLORE_2026-11-01.md`, unchanged:
short when the 1h close crosses under its 480-hour EMA on a bear day (BTC 20-day return <= 0), 10M USDT 24h volume,
stop 6%, exit after 168 hours, one trade per coin at a time, 0.20% round trip + real funding, the 19 coins of Amendment A1.

It failed the scan's months rule (22/47) and was picked after seeing the scan, so this is a new, separate trial.
Window: 2026-04-01 → 2026-09-30, never used by the scan. **One look.**

## Pass rule (fixed now, as written in the exploration register)
>= 20 trades and average net per trade > 0 at 2x costs (0.40% round trip + funding).
Also reported (no gate): base-cost average, months positive, worst trades first, BTC move over the window.
Pass → 🟠 → step 2 (300 USDT / 6-slot replay). Fail → 🔴, the idea is closed.

## Result
Run 2026-11-01, one look. Trades in `explore/heldback_T_ema480_h168_s6.csv`.
- 118 trades, average net **-0.39%** per trade, at 2x costs **-0.59%**, win rate 36.4% -> **FAIL -> 🔴, idea closed.**
- Months (sum of trade %): 2026-04 -65.0, 05 +40.6, 06 +105.4, 07 -49.9, 08 -6.7, 09 -70.6 (2 of 6 positive).
- Worst: WLD 2026-09-11 -6.3%, WLD 2026-05-28 -6.2%, ZEC 2026-05-27 -6.2%, ETH 2026-04-02 -6.2%, ARB 2026-07-04 -6.2%.
  Best: WLD 2026-06-23 +24.1%, ZEC 2026-06-04 +21.4%, ENA 2026-06-04 +20.7%.
- Context: BTC 68,288 -> 83,577 over the window, 44% bear days; no crash month like 2022-05 / 2025-03 / 2025-11.
  Same crash-catcher profile as in the scan: June paid, the other months lost.
