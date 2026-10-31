# Forward test: VBreak4 shorts in Bear-Calm — registered 2026-10-11, before the paper bot started

Michael: "yes stop it and set up the paper bot" (2026-10-11). PAPER ONLY (dry-run, no key, port 8111).

## Why a forward test
Bear days are ~48% of the time and nothing tested earns in them; the live bot holds cash then. The one hint: in the
2026-10-11 conditions test, VBreak4's Bear-Calm shorts on top-133 coins were PF 1.32 over 2,181 trades (longs PF 0.89).
That split was seen after the fact, and every good coin has already been used by VBreak4, so no fair past test is left
for good coins. (A test on 266 never-used coins was registered the same day and CANCELLED before any result: those
coins are young/small and not what the bot would trade. See research/BEARCALM_FRESH_CANCELLED_2026-10-11.md.)

## What runs (frozen)
`bots/strategies/VBreak4BearCalmShort.py` = live VBreak4Live code imported unchanged + two refuse-only rules: no longs;
shorts only while BTC is Bear-Calm (`bullcalm_rule.market_condition`). Preset `bots/presets/vbreak4-bearcalm-short.json`:
the live bot's 127 coins, 20 slots (<= 10 shorts by the VBreak4Live cap), 300 USDT paper wallet, stake = balance/20.
No change to code or preset while the test runs; a fix for a crash is allowed and logged here.

## Verdict (one look, whichever comes first)
- after 100 closed trades, or
- on 2027-04-11 (decision date), whatever the count.
PASS (🟡 → Michael decides about real money) if all: >= 50 closed trades; profit factor >= 1.15 (old-bot dry-run
fees); paper wallet above 300; max drawdown <= 30%; not more than half of the profit from one week.
Fewer than 50 trades by 2027-04-11: no verdict, Michael decides whether to extend (the market may not have been
Bear-Calm often). FAIL: 🔴, bear markets = cash, the bot is stopped and the preset removed.
Dry-run has no slippage, so a pass is an upper bound; real money would still start small.
