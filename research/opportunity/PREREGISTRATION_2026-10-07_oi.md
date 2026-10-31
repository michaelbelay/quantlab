# Pre-registration: open-interest conditions (item 9), 2026-10-07

**Status: RUN 2026-10-07 - 0 yellow, 2 orange, 6 red. See OI_RESULT_2026-10-07.md.**

Written **before** any OI condition was computed or any result seen. After this file is committed to the
hash list below, the definitions, windows, fit rule and badge rule do not change. A defect found later is
reported, not silently fixed.

## Question
Do sudden open-interest (OI) changes or extreme taker / top-trader positioning give a direction (LONG or
SHORT) that survives costs on 1h futures, better than random entries?

## Data (local, no download)
- `user_data/desk_data/<COIN>/`: 30 USDT-M perps (desk universe, `universe.json`), 2024-09-01 .. 2026-09-25.
  - 1h bars = 15m klines resampled (open first, high max, low min, close last, volume sum).
  - funding = `funding.parquet` (`rate`), same funding cost as the playbook.
  - OI and ratios = `metrics_5m.parquet`, value at the last 5m stamp of each hour (`oi` in contracts,
    `taker_ls`, `top_ls_positions`, `global_ls`).
- **Sealed quadrant is never read:** for ETH SOL ENA SUI RARE TAO FIL LTC 1000PEPE QNT DASH ARK AAVE SAGA FET
  only rows with date < 2026-03-26 00:00 UTC are loaded (filter applied inside the parquet read).
- **Liquidations:** no liquidation history exists locally and Binance's REST API offers none. The OI-flush
  conditions below are the proxy (OI falls hard while price moves hard = positions forced out). Real
  liquidation data would need a live websocket recorder; out of scope here.
- 280 unseen OOS coins have no OI data locally → **no unseen-coin test is possible**. A rule can only move
  beyond its dev badge through the forward test.

## Conditions (8, fixed; all hourly, on bar close)
Helpers: `doi4 = log(oi / oi 4h ago)`; `zoi = doi4 / std(doi4 over last 720h, min 500)`;
`z4 = 4h log return / (sigma24 * sqrt(4/24))` with `sigma24` exactly as in `common.py`;
`pct(x)` = rank of x within its last 720 hours (min 500).

| Name | Definition | Plain meaning |
|---|---|---|
| OI_BUILD_UP | zoi ≥ 3 and z4 ≥ +1 | new positions pour in while price rises |
| OI_BUILD_DN | zoi ≥ 3 and z4 ≤ −1 | new positions pour in while price falls |
| OI_FLUSH_DN | zoi ≤ −3 and z4 ≤ −1.5 | positions forced out in a drop (long-liquidation proxy) |
| OI_FLUSH_UP | zoi ≤ −3 and z4 ≥ +1.5 | positions forced out in a rise (short-squeeze proxy) |
| TAKER_BUY_X | pct(4h mean taker_ls) ≥ 0.99 | aggressive buying at a 30-day extreme |
| TAKER_SELL_X | pct(4h mean taker_ls) ≤ 0.01 | aggressive selling at a 30-day extreme |
| TOP_LONG_DIV | pct(top_ls_positions) ≥ 0.95 and pct(global_ls) ≤ 0.05 | big accounts long, crowd short |
| TOP_SHORT_DIV | pct(top_ls_positions) ≤ 0.05 and pct(global_ls) ≥ 0.95 | big accounts short, crowd long |

Trigger = condition switches on, 48h cooldown per coin (`common.triggers`). Entry = open of the next hour.

## Rule fit and test (identical to the playbook)
- Fit window: 2024-10-01 .. 2025-07-01 (first month is warm-up). Test window: 2025-07-01 .. 2026-09-25.
- Fit: `build_playbook.fit_rule` — 2 directions × 3 time limits (8/24/48h), target = median favourable move,
  stop = 80th pct adverse move of winners (sigma24 units). 8 conditions × 6 = **48 trials**.
- Costs 0.2% round trip + funding; stop counts first if both hit in one hour.
- Random baseline: 300 random entries per coin, same windows and bracket.
- Periods for the "regimes" check (4 quarters-pairs): 2024-10..2025-04, 2025-04..2025-10, 2025-10..2026-04,
  2026-04..2026-09-25.

## Badge (same rule as the playbook, plus clusters)
- 🔴 fit avg ≤ 0, test avg ≤ 0, or < 30 test cases.
- 🟠 positive but fails one of: test day t ≥ 2; beats random by ≥ 0.10 pp; ≥ 3/4 periods positive;
  **test event-avg > 0** (event = same condition, same trigger hour; coins averaged first).
- 🟡 passes all. Not tradeable on its own: only 30 coins and ~15 months of test. 🟢 never from this study.
- Multiple testing: 48 fit trials, 8 frozen rules tested. With no real edge, each rule has ~2.3% chance of
  day t ≥ 2 (one-sided), so ~0.2 false 🟡 expected; overlapping days make that optimistic. A 🟡 here therefore
  goes to the forward test only, never straight to a real order.

## Outputs
`oi_study.py` → `oi_playbook.json`, `oi_summary.csv`, `OI_RESULT_2026-10-07.md`.
