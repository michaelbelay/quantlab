import json, warnings, pandas as pd
warnings.filterwarnings('ignore')
from engine import load_daily, full_report
import strats as S
D = load_daily(); C = json.load(open('coins.json')); dev = C['dev']
grids = {
 'TREND_GATED': [dict(lb=lb, n_sma=ns, every=ev, method=m) for lb in (20, 50, 100) for ns in (50, 100, 200) for ev in (1, 7) for m in ('ema', 'ret')],
 'DUAL_MOM': [dict(lb=lb, n=n, every=ev, n_sma=ns) for lb in (14, 30, 60) for n in (3, 5, 8) for ev in (7, 14) for ns in (50, 100, 200)],
}
fn = {'TREND_GATED': S.trend_gated, 'DUAL_MOM': S.dual_mom}
rows = []
for fam, g in grids.items():
    for p in g:
        rep, _ = full_report(fn[fam](D, dev, **p), D, fam); rep.update(fam=fam, params=json.dumps(p)); rows.append(rep)
df = pd.DataFrame(rows); df.to_csv('dev_grid2.csv', index=False)
pd.set_option('display.width', 250)
cs = ['params','pf','pf_2xcost','pf_2xfund','trades','sharpe','cagr','maxdd','total','reg_2021','reg_2022','reg_2023_24','reg_2025_26']
for fam in grids:
    d = df[df.fam == fam]
    print('\n==', fam, 'median total', round(d.total.median(), 3), 'median sharpe', round(d.sharpe.median(), 2))
    q = d[d.pf_2xcost >= 1.05].sort_values('sharpe', ascending=False)
    print(q[cs].head(6).round(3).to_string(index=False))
