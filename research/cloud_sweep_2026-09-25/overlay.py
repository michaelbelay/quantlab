import numpy as np, pandas as pd
from engine import run
def vt(W, D, target=0.20, cap=1.0, win=30):
    base = run(W, D)['port']
    rv = base.rolling(win, min_periods=15).std() * np.sqrt(365)
    sc = (target / rv).replace([np.inf], np.nan).fillna(0).clip(upper=10)
    g = W.abs().sum(axis=1)
    sc = np.minimum(sc, (cap / g).replace([np.inf], np.nan).fillna(0))
    return W.mul(sc, axis=0)
def blend(Ws, D, target=0.20, cap=1.0):
    parts = [vt(W, D, target=target, cap=10) for W in Ws]
    tot = sum(p.reindex(columns=D['close'].columns).fillna(0) for p in parts)
    return vt(tot, D, target=target, cap=cap)
