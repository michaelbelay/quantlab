import itertools, json, time, warnings
import pandas as pd, numpy as np
warnings.filterwarnings('ignore')
from engine import load_daily, split, full_report
import strats as S
D = load_daily()
dev, hold = split()
cols = set(D['close'].columns)
dev = [c for c in dev if c in cols]; hold = [c for c in hold if c in cols]
print(len(dev), 'dev', len(hold), 'hold', flush=True)
json.dump(dict(dev=dev, hold=hold), open('coins.json', 'w'))

grids = {
 'XS_MOM': [dict(lb=lb, skip=sk, n=n, every=ev, ivol=iv) for lb in (14, 30, 60, 90) for sk in (1,) for n in (3, 5, 8) for ev in (7, 14) for iv in (False, True)],
 'XS_MOM_LONG': [dict(lb=lb, skip=1, n=n, every=ev, long_only=True, btc_filter=True) for lb in (14, 30, 60, 90) for n in (3, 5, 8) for ev in (7, 14)],
 'CARRY': [dict(lb=lb, n=n, every=ev, ivol=iv) for lb in (3, 7, 14, 30) for n in (3, 5, 8) for ev in (1, 7) for iv in (False, True)],
 'TS_TREND': [dict(lb=lb, target_vol=0.3, long_only=lo, every=ev, method=m) for lb in (20, 50, 100, 200) for lo in (False, True) for ev in (1, 7) for m in ('ret', 'ema')],
 'XS_REV': [dict(lb=lb, n=n, every=ev) for lb in (1, 3, 5) for n in (3, 5, 8) for ev in (1, 3)],
}
fn = {'XS_MOM': S.xs_mom, 'XS_MOM_LONG': S.xs_mom, 'CARRY': S.carry, 'TS_TREND': S.ts_trend, 'XS_REV': S.xs_rev}
rows = []
for fam, g in grids.items():
    t0 = time.time()
    for p in g:
        W = fn[fam](D, dev, **p)
        rep, _ = full_report(W, D, fam)
        rep.update(fam=fam, params=json.dumps(p))
        rows.append(rep)
    print(fam, len(g), f'{time.time()-t0:.0f}s', flush=True)
df = pd.DataFrame(rows)
df.to_csv('dev_grid.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
cols_show = ['fam','params','pf','pf_2xcost','pf_2xfund','trades','sharpe','cagr','maxdd','total','reg_2021','reg_2022','reg_2023_24','reg_2025_26','turnover_yr']
for fam in grids:
    d = df[df.fam == fam]
    print('\n==', fam, 'median total', round(d.total.median(), 3), 'median sharpe', round(d.sharpe.median(), 2), 'share PF2x>=1.05', round((d.pf_2xcost >= 1.05).mean(), 2))
    print(d.sort_values('sharpe', ascending=False)[cols_show].head(6).round(3).to_string(index=False))
