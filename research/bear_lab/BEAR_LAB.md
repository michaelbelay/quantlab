# Bear lab (built 2026-11-02; Michael: work in the background, daily, "dont come until you find a solution")

Daily loop, no human in it. Michael hears from it only when an idea passes on live data (Windows toast + `PASSED.md`).

```
 09:30 daily  OI collector update -> evaluate all paper ideas on live data -> discovery agent writes up to 6 ideas,
              screens them, enters up to 3 -> report
```

## Rules
- Coins: the trader's 19 (RULES_BEAR A1). Shorts only. Entries only on bear days (BTC 20-day return <= 0 at the last
  daily close). Engine (`bear_lab.py`, fixed): entry at the signal bar's close, hard stop checked first, optional
  target, max hold, 0.20% round trip, real funding, 10M USDT 24h volume, one trade per coin at a time.
- **Screen (light, history 2022-01 → 2026-09):** >= 100 trades, >= 30 in each half (split 2024-05-01), average net
  > 0 in both halves, > 0 at 2x costs. Every screen is logged; the count is in every report.
- **Paper:** an idea that passed its screen is frozen (sha256 of the idea and of `bear_lab.py`) and paper-trades from
  the hour it entered, on the scanner's live candles + funding and the OI collector's data. Only trades entered after
  that hour count. A changed file or engine → ⛔ TAMPERED.
- **Verdict (new data only):** after >= 40 closed trades on >= 12 entry days: day-weighted average <= 0 → 🔴 KILLED;
  day-weighted average > 0 **and** day t >= 2.5 **and** average > 0 at 2x costs → 🟡 PASS (toast + PASSED.md).
  No verdict after 180 days → ⚪ EXPIRED. t >= 2.5 (not 2.0) because many ideas run at once.
- 🟡 PASS is not live: next is the 300 USDT replay, then Michael decides. Nothing in this lab trades.
- **t (2026-11-13):** the reported `day_t` is the smaller of the usual t and the one-sided sign test on the daily
  means. A fixed take-profit makes every win the same size, which collapsed the spread and sent t to 1713 on 7
  trades; the cap bounds the claim by how many days were positive. `min_t` stays 2.5. See `discovery_log.md`.

## Files
`bear_lab.py` (engine, commands) · `BEAR_DISCOVERY_PROMPT.md` (the agent's instructions) · `ideas/` · `bear_lab.db`
(ideas, screens, evals) · `state.json` · `REPORT_latest.md` · `PASSED.md` · `discovery_log.md` · `logs/daily.log`.
Task: "Quantlab Bear Lab Daily" (`bear_daily.bat`, registered with `register_task.ps1`).

## Engine check (2026-11-02)
The scan variant T_ema480|h168|s6 run through this engine gives 781 trades +0.791% (2022-01..2026-03) and 118 trades
-0.39% (2026-04..09) – identical to `bear_explore.py` and the held-back check.
