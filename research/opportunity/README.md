# Opportunity engine (built 2026-10-06)

Scans the top Binance USDT perpetuals for fixed, measurable market conditions and,
for each fresh trigger, prints the **direction, entry, target, stop and time limit**
plus the facts behind them: how often this happened before, what happened next,
and how it compares with random entries. Michael decides; nothing is traded.

| File | What it does |
|---|---|
| `common.py` | The 13 conditions + bracket simulator. Same code for history and live. |
| `build_playbook.py` | Builds `playbook.json` from the 133 dev coins (1h futures + funding). |
| `scan.py` | Live scan, Binance public data (no API key), cache in `live_cache/`. Writes `latest_scan.json`. |
| `PREREGISTRATION_2026-10-06_unseen.md` | Frozen test on the 280 unseen coins. **Not run yet.** |

```
.venv\Scripts\python.exe research\opportunity\build_playbook.py      # ~40 s
.venv\Scripts\python.exe research\opportunity\scan.py --top 200      # ~1-2 min when cached; --all shows 🔴 too
```

## How a rule is set (no grid search)
1. Fit window = before 2025-01-01. For each condition, try 2 directions x 3 time limits (8/24/48 h).
   Target = median favourable move, stop = 80th percentile adverse move of trades that ended in profit,
   both in units of the coin's normal daily move (sigma24). Keep the best of the 6. Total 78 trials.
2. Test window = 2025-01-01 → 2026-09-21. The frozen rule, never seen by step 1.
3. Entry = open of the next hour after the trigger. Costs 0.2% round trip + funding paid while open.
   If target and stop are hit in the same hour, the stop counts.
4. `day t` averages all trades of one day first, so 40 coins crashing together count as one day, not 40 wins.

## Badge (stated before results)
🔴 loses on fit or test, or < 30 test cases · 🟠 positive but fails one of: day t ≥ 2, beats random by ≥ 0.10 pp,
≥ 3/4 regimes positive · 🟡 passes all · 🟢 never from dev data alone: needs the unseen-coin test + forward test.

## First results (2026-10-06): 0 🟡, 4 🟠, 9 🔴

| Condition | Rule | Test avg/trade | Median | Day t | Random | Regimes | Badge |
|---|---|---|---|---|---|---|---|
| VOLSPIKE_DN: volume 3x, price down | LONG 48h | **+0.39%** | −1.59% | +1.78 | −0.20% | 4/4 | 🟠 closest |
| BRK_LO20: 20-day low break | SHORT 48h | +0.18% | −0.21% | −4.17 | −0.18% | 4/4 | 🟠 crash days only |
| SQUEEZE: very low volatility | SHORT 48h | +0.03% | −0.53% | −1.53 | −0.20% | 3/4 | 🟠 |
| FUND_DIV_UP: neg. funding, price up | LONG 24h | +0.05% | −1.07% | +0.66 | −0.22% | 2/4 | 🟠 |
| all funding-crowding rules, PUMP, DUMP, BRK_HI20, VOLSPIKE_UP | | ≤ 0 or day t < 0 | | | | | 🔴 |

Notes: DUMP made +0.62% in 2021-24 and lost −0.64% in 2025-26, the split caught it.
Funding extremes alone do not give a direction (matches the quantlab F1-F5 result).

## Lessons from building
- Binance returns at most 1,000 1h candles per request: the first scan used stale August data.
  Fixed; `scan.py` now refuses any coin whose last closed candle is > 2h15m old.

## 2026-10-07: unseen-coin test + forward test (the scanner judges itself)
- **Unseen test (pre-registered): FAIL.** VOLSPIKE_DN on 280 unseen coins: −0.13%/trade, day t −0.29 → 🔴.
  No rule reaches day t ≥ 2 on unseen coins → all 13 rules are 🔴 (stricter than registered, by request). `UNSEEN_RESULT_2026-10-07.md`.
- **Forward test** (`forward.py`, `forward.db`): every trigger of every rule is logged (badge at the time, entry = open
  after the trigger, target/stop/time limit) and resolved on real candles at each scan, incl. costs and funding.
- **Effective badge** (`badges.json`, stated before any forward result): dev badge → 🔴 if it failed the unseen test →
  after ≥ 50 closed trades on ≥ 20 days: day-avg ≤ 0 → 🔴 "killed"; day-avg > 0 and day t ≥ 2 → 🟡 "confirmed forward".
  🟢 only after a human review. A rule can only come back through forward evidence.
- **Hourly automatic scan**: Windows task "Quantlab Hourly Scan" at :02 → `scan.py --auto` (log: `scan_auto.log`,
  lock: `scan.lock`). Windows notification for new tradeable (non-🔴) alerts; `config.json` `notify_all: true` notifies
  every trigger. Remove with: `Unregister-ScheduledTask -TaskName "Quantlab Hourly Scan"`.
- UI (quantlab :8500, Scanner tab): forward scoreboard per rule + forward log.

## 2026-10-07 (later): bug fix + clustered alerts
- **Fix:** the 04:02 and 05:02 UTC auto-scans skipped ~191/200 coins (`MergeError`): pandas 3 stored candle times in ms and
  funding times in µs, and `merge_asof` refuses to join them. `scan.py` loaders now convert both to ns. `common.py` unchanged
  (sha b96f2c04). The 05:15 rerun logged the 11 missed triggers.
- **Clusters (item 4):** same rule + same trigger hour on ≥ 3 coins (`forward.CLUSTER_MIN`) = one market event.
  Scanner prints it as one group (two most liquid coins in full), one toast per event, red list grouped by rule.
  `forward_stats` adds `events`, `event_avg_pct`, solo vs cluster averages. Badge rule unchanged (still day-weighted).
  Backups: `scan.py.bak_cluster`, `forward.py.bak_cluster`.

## 2026-10-07: item 9, open-interest conditions (pre-registered) - nothing passes
8 OI / taker / top-trader conditions on the 30 desk coins (`oi_study.py`, `PREREGISTRATION_2026-10-07_oi.md`):
0 🟡, 2 🟠 (top-trader vs crowd divergence → SHORT 48h, +0.1%/trade, t < 1), 6 🔴. Not added to the live scanner.
Details: `OI_RESULT_2026-10-07.md`.

## 2026-10-07: Binance Web3 feeds (smart money, trending, hype)
- **Smart-money buy signals (on-chain tokens): fact-checked, they lose.** 158 signals, buy 2 min after the alert:
  median −63% after 4h, −79% after 24h; the feed's own prices say −93% median. `SMART_MONEY_RESULT_2026-10-07.md`.
- **Trending / inflow / hype boards** have no history API → `web3_recorder.py` snapshots them every hour (called by
  `scan.py --auto`, data in `web3_feed.db`). Test fixed in advance: `PREREGISTRATION_2026-10-07_web3.md`
  (coins with a Binance perp, market-adjusted 4h/24h move, decided after ≥ 4 weeks and ≥ 50 events).
