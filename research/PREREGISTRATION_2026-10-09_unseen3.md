# Pre-registration: 3 incubator ideas on the 280 unseen coins, 2026-10-09

Written before the run. Michael's explicit go: "yes go ahead, use the unseen coins" (2026-10-09).
Run once; no re-runs, no changes after seeing results. Frozen files + sha256 in `research/unseen3/hashes.txt`.

## Why
Forward incubation needs weeks; Michael wants an answer in days. The unseen coins (`oos_universe.json["kept"]`)
have never been used for these three ideas (earlier use: 13 scanner rules 2026-10-07, focus/val1 pipeline sets).

## Ideas (exactly the frozen incubator files, unchanged)
1. `flush_f1.py` — F1 crash bounce: DN days, coin 24h return <= -2.5 sigma with 24h volume >= 3x, long 24h, stop 1.5 sigma.
2. `absorption_up.py` — volume absorption: UP days, 24h volume >= 3x with |24h return| <= 0.5 sigma, above 20-day avg, long 48h.
3. `channel_uphivol.py` — pipeline candidate 602db68df71a (channel, not_flat, long), only on UP_HIVOL days.

## Data and mechanics
- 280 unseen coins (`user_data/oos_data`), 2021-01-01 .. 2026-09-25 (entry time). Market types: `regime_switch.market_types`
  (BTC daily, shifted 1 day). Same simulation as the incubator (`incubator.idea_trades`): 0.2% round trip, stop slip,
  funding, no stacking, entry at next open. Engine trades still open at data end are dropped.

## Pass rule (per idea; t raised to 2.4 because 3 ideas are tested)
trades >= 100, day-average > 0, day t >= 2.4, PF at 2x costs >= 1.0, and day-average still > 0 after removing the
3 best days. Reported but not deciding: random-entry percentile (same days, random coins/hours, 200 reps, rule ideas only),
yearly results.

## Consequences
- Pass → 🟡 research lead: keeps incubating on live data; next step 300 USDT simulation; Michael decides. No trading.
- Fail → 🔴: we stop counting on it (the incubator keeps logging it untouched, so its forward record still builds).
- The unseen coins are then spent for these 3 ideas. No variant of them may be tested on these coins again.
