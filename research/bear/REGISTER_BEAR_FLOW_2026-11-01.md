# Bear ideas – batch 3, order flow (registered 2026-11-01 before the run; Michael: "try the order flow data")

Rules: `RULES_BEAR.md`, unchanged (bear day = BTC 20-day return <= 0; 2022-01 → 2026-09, halves A 2022-01..2024-04 /
B 2024-05..2026-09; 0.20% round trip + funding; stop checked first; gates and 🔴🟠🟡🟢 as written).

## Data
- `data/market/flow/<coin>.feather`: 1h taker buy volume (aggressive buyers) and total volume, 2021-01 → 2026-09-30.
  It covers the full test period, so no rule changes are needed.
- Coins: the 122 coins of batches 1–2 minus 4 without flow data (ATH, IOTA, TWT, UAI) = **118 coins**.
- Not used: open interest (only 2025-06..07 in the files) and the desk positioning set (30 coins from 2024-09) –
  too short for these rules.

## Measures
- **Buy share 24h (BS24)** = taker buy quote volume / total quote volume over the last 24 hours (0.5 = balanced).
- **BS24 rank** = where BS24 sits among the coin's own values over the previous 720 hours (0 = lowest, 1 = highest).
  Ranks are used so every coin is judged against itself.
- **Delta72** = aggressive buys minus aggressive sells (quote volume) over the last 72 hours.
- SMA20d = average of the last 480 1h closes. Every entry: bear day + 10M USDT 24h volume.

## Ideas (all numbers fixed now)
| # | name | idea in one line | entry (short, on a closed 1h candle) | stop / hold |
|---|---|---|---|---|
| F1 | covering_rally | bounce driven by shorts covering, not buyers | coin below SMA20d, 24h return >= +5%, BS24 rank <= 0.30. One per coin per 24h | 8% / 48h |
| F2 | absorbed_buying | buyers hit hard but price does not rise: sellers soak it up | BS24 rank >= 0.90 and 24h return <= 0 | 6% / 48h |
| F3 | delta_divergence | price makes a 72h high while net flow is selling | close = highest close of the last 72h and Delta72 < 0 | 72h high × 1.02 / 72h |
| F4 | market_euphoria | whole market buys aggressively in a bear | market BS24 (50 biggest coins by 24h volume, summed) rank >= 0.90, first such hour in 24h: short the 10 coins with the highest own BS24 | 8% / 48h |
| F5 | persistent_selling | a week of steady aggressive selling | 7-day buy share rank (vs previous 720h) <= 0.10, coin below SMA20d, 7-day return < 0. One per coin per 72h | 8% / 72h |

Expected trade counts (rough): F1 ~1,000 · F2 ~3,000 · F3 ~1,500 · F4 ~400 · F5 ~1,500.

## Gates (RULES_BEAR.md, step 1)
>= 150 trades and >= 50 per half · average net trade >= +0.30% in both halves · positive at 2x costs · >= 55% of bear
months positive. A 1x short cannot lose more than 100% (liquidation): any trade below -100% is reported and also shown capped.

## Stated before the run
- 5 more trials (bear total 16). After 11 failures the honest prior is that most or all of these fail too.
- F2 is related in spirit to the incubator idea "Volume absorption (UP, long)" (heavy volume, no price move; running
  forward at -0.78% per day), but uses taker flow direction and is a short in a bear.

## Result
Run 2026-11-01, `bear_flow.py`, rules unchanged, 118 coins. Trades in `batch3/`. No trade below -100%.

| # | trades (A / B) | win | avg net | half A | half B | 2x costs | bear months + | USDT @50/trade | verdict | fails |
|---|---|---|---|---|---|---|---|---|---|---|
| F1 covering_rally | 1005 (206 / 799) | 48.2% | -0.533% | -0.864% | -0.447% | -0.733% | 18/46 | -267.7 | 🔴 | avg net < +0.30% in a half, loses at 2x costs, bear months positive < 55% |
| F2 absorbed_buying | 5648 (2146 / 3502) | 41.9% | -0.557% | -0.511% | -0.585% | -0.757% | 15/53 | -1573.1 | 🔴 | avg net < +0.30% in a half, loses at 2x costs, bear months positive < 55% |
| F3 delta_divergence | 11530 (3767 / 7763) | 27.8% | -0.17% | -0.366% | -0.075% | -0.37% | 23/53 | -982.5 | 🔴 | avg net < +0.30% in a half, loses at 2x costs, bear months positive < 55% |
| F4 market_euphoria | 2173 (913 / 1260) | 44.3% | -0.803% | -0.888% | -0.741% | -1.003% | 15/50 | -872.2 | 🔴 | avg net < +0.30% in a half, loses at 2x costs, bear months positive < 55% |
| F5 persistent_selling | 4069 (1556 / 2513) | 46.2% | -0.194% | 0.776% | -0.794% | -0.394% | 18/53 | -394.7 | 🔴 | avg net < +0.30% in a half, loses at 2x costs, bear months positive < 55% |

By year (avg net per trade, %):

- F1 covering_rally: 2022 -1.38 (148), 2023 +1.14 (22), 2024 -0.47 (214), 2025 -0.16 (490), 2026 -1.37 (131) · worst: SENT 2026-01-29 -9.41%, M 2025-08-20 -8.87%, AXS 2026-02-25 -8.58%
- F2 absorbed_buying: 2022 -0.62 (974), 2023 +0.05 (713), 2024 -0.76 (1331), 2025 -0.82 (1840), 2026 -0.08 (790) · worst: SOL 2022-11-10 -10.2%, SOL 2022-11-10 -8.2%, SOL 2022-11-10 -8.2%
- F3 delta_divergence: 2022 -0.44 (1767), 2023 -0.20 (1285), 2024 -0.47 (2397), 2025 +0.12 (4019), 2026 -0.14 (2062) · worst: FET 2025-11-07 -16.34%, H 2026-06-06 -15.54%, VIRTUAL 2025-04-11 -15.23%
- F4 market_euphoria: 2022 -1.23 (477), 2023 -0.68 (344), 2024 -0.72 (416), 2025 -0.52 (600), 2026 -0.92 (336) · worst: ZRO 2025-03-15 -10.05%, M 2025-09-10 -9.93%, ONDO 2025-01-14 -9.09%
- F5 persistent_selling: 2022 +1.15 (634), 2023 +1.17 (706), 2024 -1.32 (649), 2025 -1.12 (1310), 2026 -0.03 (770) · worst: AXS 2026-02-19 -14.5%, SENT 2026-02-07 -11.49%, H 2025-12-07 -9.5%

Check (report only): F5 ETC 2026-09-15 recomputed by hand (7-day buy share 0.466, rank 0.06, 7-day return -16.3%, below SMA20d; stop +8% hit) - matches.
Verdict: all five 🔴. F5 persistent_selling earned in half A (+0.78% per trade; 2022 +1.15%, 2023 +1.17%) and lost in half B (-0.79%; 2024 -1.32%, 2025 -1.12%).
