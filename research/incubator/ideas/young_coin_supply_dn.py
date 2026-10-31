"""Young-coin supply overhang (discovery 2026-10-19).
Idea: a coin 60-120 days after its first futures candle, below its 20-day average and down over 7 days, is shorted
for 72h (first hour the condition holds). Any market type.
Reason: in the months after listing, airdrop receivers, early investors and unlock schedules are steady forced sellers
while the listing hype buyers are gone; every new listing goes through this, so it repeats."""
NAME = "Young-coin supply (all markets, short 72h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = -1, 72, 2.0, None


def signals(g):
    age = g["hist"]
    young = (age >= 60 * 24) & (age < 120 * 24)
    m = young & (g.close < g.sma480) & (g.ret168 < 0)
    return m & ~m.shift(1, fill_value=False)
