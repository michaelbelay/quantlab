import json, warnings, pandas as pd, numpy as np
warnings.filterwarnings('ignore')
from engine import load_daily, full_report
import strats as S
from overlay import vt, blend
D = load_daily(); C = json.load(open('coins.json'))
def picks(coins):
    return {
     'XS_MOM': S.xs_mom(D, coins, lb=14, skip=1, n=5, every=14),
     'XS_MOM_LONG': S.xs_mom(D, coins, lb=14, skip=1, n=5, every=14, long_only=True, btc_filter=True),
     'CARRY': S.carry(D, coins, lb=7, n=8, every=7, ivol=True),
     'TS_TREND': S.ts_trend(D, coins, lb=20, target_vol=0.3, long_only=True, every=1, method='ema'),
    }
def variants(coins):
    p = picks(coins); out = {}
    for k, W in p.items():
        out[k] = W; out[k + '+VT'] = vt(W, D)
    out['BLEND(MOM,CARRY,TREND)+VT'] = blend([p['XS_MOM'], p['CARRY'], p['TS_TREND']], D)
    out['BLEND(MOM,CARRY)+VT'] = blend([p['XS_MOM'], p['CARRY']], D)
    return out
if __name__ == '__main__':
    import sys
    which = sys.argv[1]
    coins = C[which]
    rows = []
    for k, W in variants(coins).items():
        rep, r = full_report(W, D, k); rep['gross'] = W.abs().sum(axis=1).loc['2021-03':].mean(); rows.append(rep)
    df = pd.DataFrame(rows)
    df.to_csv(f'final_{which}.csv', index=False)
    pd.set_option('display.width', 250)
    print(df[['label','pf','pf_2xcost','pf_2xfund','trades','win','sharpe','cagr','maxdd','total','reg_2021','reg_2022','reg_2023_24','reg_2025_26','gross']].round(3).to_string(index=False))
