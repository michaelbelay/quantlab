# Scalp lab (built 2026-11-06; Michael: "update the scanner to create scalps", bear market, both sides)

Every 5 minutes, no human in it. A rule that passed its history screen sends **live scalp alerts** (Windows toast:
coin, side, entry, stop, target, exit-by time) and paper-trades itself on the same live candles. Michael decides on any
alert; nothing in this lab places orders.

```
 every 5 min  5m candles for the 19 coins (Binance public) -> each live rule: signals on the last closed bar ->
              new alert = toast + latest_scalps.json -> paper trades since entry -> verdict -> REPORT_latest.md
```

## Rules
- Coins: the bear lab's 19 (trader list minus 1000PEPE). Long and short. Entries only on bear days (BTC 20-day return
  <= 0 at the last daily close, the bear lab rule). Engine (`scalp_lab.py`, fixed): entry at the signal bar's close,
  hard stop checked first inside a candle, optional target, max hold 48 bars (4h), **0.14% round trip** (taker 0.05%
  x 2 + slippage 0.02% x 2), real funding, 10M USDT 24h volume, one trade per coin at a time.
- **Screen (history 2024-02 → 2026-09, 5m):** >= 200 trades, >= 60 in each half (split 2025-06-01), average net > 0
  in both halves, > 0 at 2x costs (0.28%). Every screen is logged; the count is in every report.
- **Live:** a rule that passed is frozen (sha256 of the rule and of `scalp_lab.py`) and alerts + paper-trades from
  the 5-minute bar it entered. Only trades entered after that count. A changed file or engine → ⛔ TAMPERED.
- **Verdict (new data only):** after >= 60 closed trades on >= 10 entry days: day-weighted average <= 0 → 🔴 KILLED
  (alerts stop); > 0 **and** day t >= 2.5 **and** > 0 at 2x costs → 🟡 PASS (toast + PASSED.md). A 🟡 rule that drops
  to day average <= 0 is killed. No verdict after 120 days → ⚪ EXPIRED.
- 🧪 alerts are from rules not yet proven on live data. Earlier scalp test (2026-10-29, 5 families, all days, 20 coins):
  all lost after taker fees. That is why every rule here must survive costs in both halves before it alerts.

## Files
`scalp_lab.py` (engine, commands) · `ideas/` · `scalp_lab.db` (ideas, screens, evals, alerts) · `live_5m/` (live
candles) · `latest_scalps.json` (open scalps + new alerts, read by the UI) · `state.json` · `REPORT_latest.md` ·
`PASSED.md` · `REGISTER_SCALP_BEAR_2026-11-06.md` · `logs/scan.log`. Task: "Quantlab Scalp Scan" (`scalp_scan.bat`,
every 5 min, registered with `register_task.ps1`).
