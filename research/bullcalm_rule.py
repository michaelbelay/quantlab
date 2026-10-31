"""The Bull-Calm market condition used by VBreak4BullCalm - plain pandas, no bot imports, so the UI status
(live_status.py) and the parity check (research/vbreak_bullcalm_check.py) run the exact same code quickly.

Definition = research/vbreak_conditions.py btc_conditions(), from BTC DAILY closes:
  Bull : 20-day return > 0
  Calm : 20-day volatility (std of daily % changes) <= its median over the previous 365 days
  known at time t = the last daily candle that CLOSED at or before t.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

LOOKBACK_DAYS = 20          # 20-day return and 20-day volatility
MEDIAN_DAYS = 365           # volatility median over the previous 365 days
MEDIAN_MIN_DAYS = 300       # research: rolling(365, min_periods=300)
NEED_CANDLES = LOOKBACK_DAYS + MEDIAN_DAYS + 1      # full 365-day window, no min_periods shortcut


def market_condition(btc_daily: pd.DataFrame, now: datetime) -> dict:
    """Bull/Calm from BTC daily candles (columns date, close; date = candle OPEN time, UTC).

    Uses only candles that closed at or before `now` (a candle dated D closes at D+1 00:00).
    Returns {"ok", "bull", "calm", "ret20", "vol20", "median", "candle"}; ok=False means not enough data.
    """
    d = btc_daily[["date", "close"]].copy()
    d["date"] = pd.to_datetime(d["date"], utc=True)
    t = pd.Timestamp(now)
    t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    d = d[d["date"] + timedelta(days=1) <= t]
    d = d.drop_duplicates("date").sort_values("date").set_index("date")["close"]
    if len(d) < NEED_CANDLES:
        return {"ok": False, "candles": int(len(d))}
    ret20 = d / d.shift(LOOKBACK_DAYS) - 1
    vol20 = d.pct_change().rolling(LOOKBACK_DAYS).std()
    med = vol20.rolling(MEDIAN_DAYS, min_periods=MEDIAN_MIN_DAYS).median().shift(1)
    r, v, m = ret20.iloc[-1], vol20.iloc[-1], med.iloc[-1]
    if pd.isna(r) or pd.isna(v) or pd.isna(m):
        return {"ok": False, "candles": int(len(d))}
    return {"ok": True, "bull": bool(r > 0), "calm": bool(v <= m), "ret20": float(r), "vol20": float(v),
            "median": float(m), "candle": d.index[-1].strftime("%Y-%m-%d")}
