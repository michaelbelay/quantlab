"""F1 capitulation bounce in falling markets (= D4a / F1 of FLUSH_RESULT_2026-10-07.md, unchanged).
Test A: PF 2.54 but day t 1.02, 82% of profit from 3 market-wide crash days -> judged on new crash days.
Verdict unit is the entry day, so the rule asks for few trades but enough distinct days."""
NAME = "F1 crash bounce (DN, long 24h)"
KIND = "rule"
SIDE, HOLD, STOP_K, MARKET = 1, 24, 1.5, "DN"
RULE = {"min_trades": 30, "min_days": 10, "max_days": 730}


def signals(g):
    m = (g.ret24 <= -2.5 * g.sigma) & (g.vol24 >= 3 * g.vol24_avg30)
    return m & ~m.shift(1, fill_value=False)
