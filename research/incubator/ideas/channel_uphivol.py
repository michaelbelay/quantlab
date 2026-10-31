"""channel·not_flat·long only on UP_HIVOL days: the one cell that stayed positive in the regime-switch test
window (+2383). Post-hoc observation, so it is judged only on new data."""
NAME = "channel long in wild uptrends"
KIND = "engine"
BOOK = {"UP_HIVOL": ["602db68df71a"]}
RULE = {"min_trades": 50, "min_days": 20, "max_days": 365}
