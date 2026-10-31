"""Faster twin of channel_uphivol (2026-10-12, Michael: "speed its process"): same strategy and market type, verdict
after 10 wild-uptrend days instead of 20. Weaker evidence by design; the original keeps running with its own rule."""
NAME = "channel long in wild uptrends (fast verdict)"
KIND = "engine"
BOOK = {"UP_HIVOL": ["602db68df71a"]}
RULE = {"min_trades": 30, "min_days": 10, "max_days": 365}
