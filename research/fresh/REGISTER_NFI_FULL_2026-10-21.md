# NFI X8 on the full non-meme list, 30 months (registered 2026-10-21, before any run)

Michael 2026-10-21: "ok do 30 month test on the full non meme coin list". Question: does a bigger coin list shorten
NFI's quiet stretches (live NFI46: 0 trades 10-16..10-21; 48-coin backtest: 59% of the time inside dry spells >= 4.5 d)
while keeping its quality?

**Coins (fixed now):** `C:\quantlab\runs\c51_coins.json` (Quantlab Market tab top 250 by 24h quote volume on
2026-10-20, minus memes, minus gold tokens PAXG/XAUT) = 222 coins, **plus DOGE** (the one meme Michael allows) = 223.
Coins listed after 2024-04 join when their market starts (same as the 48-coin run). No dead/delisted coins added.

**Everything else = the 48-coin run unchanged** (`nfi_bt_chain.py`, quantlab preset nfi-x8): NostalgiaForInfinityX8
file as is (own 3x leverage, own exits), 5m, 6 slots, unlimited stake, limit orders, isolated futures, 300 USDT start,
monthly chunks 2024-04..2026-09, data from data.binance.vision in `user_data/data_nfi`.

**Reported side by side with the 48-coin run:** trades/week, median and p90 gap between entries, share of time in
dry spells >= 4.5 d, days with at least one entry, win rate, average trade, end wallet, worst drop, liquidations,
months positive, long/short split. Report only; the live bot is not changed.

**Technical note (2026-10-21, after the first trial chunk failed, before any results):** PONS and MARSCOIN are
skipped: old-bot has no leverage tiers for them ("impossible to backtest with this pair"). CT has no data in the
window (listed after 2026-09). Effective list: 220 coins.

**Technical note 2 (2026-10-21 03:51):** chunk 2026-09 failed with the compounded wallet (13.6M): 'Stake amount 2352902 too high for ARIA' (exchange max position). That month is re-run from 300 USDT (trades/quality only; not chained into the wallet path). Wallet totals of this compounding chain are not realistic (unlimited fills); judge on frequency, per-trade result and a fixed-stake book.
