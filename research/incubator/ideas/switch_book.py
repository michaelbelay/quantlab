"""Regime-switching book frozen in research/regime_switch/choice.json (REGIME_SWITCH_RESULT_2026-10-07.md):
UP_LOVOL -> streak_exhaustion·volume·long, UP_HIVOL -> channel·not_flat·long, downtrends -> cash.
Test A failed (PF 0.99), but the switch beat always-on; incubated to see whether the switch holds on new data."""
NAME = "Regime switch book (2 uptrend specialists)"
KIND = "engine"
BOOK = {"UP_LOVOL": ["9ef3c32f80d4"], "UP_HIVOL": ["602db68df71a"]}
RULE = {"min_trades": 50, "min_days": 20, "max_days": 365}
