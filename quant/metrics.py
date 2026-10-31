"""Portfolio metrics from a simulated equity curve."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .sim import START_EQUITY, Result


def summary(r: Result, start: int = 0) -> dict:
    eq = pd.Series(r.equity, index=pd.to_datetime(r.dates, utc=True)).iloc[start:].dropna()
    eq = pd.concat([pd.Series([START_EQUITY], index=[eq.index[0] - pd.Timedelta(hours=8)]), eq])
    daily = eq.resample("1D").last().dropna()
    ret = daily.pct_change().dropna()
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    final = float(eq.iloc[-1])
    cagr = (final / START_EQUITY) ** (1 / years) - 1 if final > 0 and years > 0 else -1.0
    sharpe = float(ret.mean() / ret.std() * np.sqrt(365)) if ret.std() > 0 else 0.0
    dd = float((1 - eq / eq.cummax()).max())
    by_year = eq.resample("YE").last()
    starts = pd.concat([pd.Series([START_EQUITY]), by_year.iloc[:-1].reset_index(drop=True)])
    first_year = eq.index[1].year                       # eq.index[0] is the synthetic start point
    yr = {int(d.year): round(float(v / s - 1) * 100, 1) for d, v, s in zip(by_year.index, by_year.values, starts.values)
          if d.year >= first_year}
    by_q = eq.resample("QE").last()
    q_starts = pd.concat([pd.Series([START_EQUITY]), by_q.iloc[:-1].reset_index(drop=True)])
    qtr = {f"{d.year}Q{d.quarter}": round(float(v / s - 1) * 100, 1)
           for d, v, s in zip(by_q.index, by_q.values, q_starts.values) if d >= eq.index[1]}
    return {"quarters": qtr, "quarters_positive": sum(v > 0 for v in qtr.values()),
            "final": round(final, 2), "cagr_pct": round(cagr * 100, 1), "sharpe": round(sharpe, 2),
            "max_dd_pct": round(dd * 100, 1), "years": yr, "years_positive": sum(v > 0 for v in yr.values()),
            "trades": r.trades, "stops": r.stops, "liquidations": r.liquidations, "liq_loss": round(r.liq_loss, 2),
            "fees": round(r.fees, 2), "funding_paid": round(r.funding, 2)}
