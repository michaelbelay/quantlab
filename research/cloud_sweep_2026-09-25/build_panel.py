import pandas as pd, numpy as np, glob, os, json
B='/mnt/user-data/uploads/quantlab/data/market/dev_1h/binance/futures/'
files=sorted(glob.glob(B+'*-1h-futures.feather'))
close,opn,high,low,vol,fund={}, {}, {}, {}, {}, {}
for f in files:
    sym=os.path.basename(f).split('_USDT_USDT')[0]
    d=pd.read_feather(f).set_index('date')
    d.index=pd.to_datetime(d.index,utc=True)
    close[sym]=d['close']; opn[sym]=d['open']; high[sym]=d['high']; low[sym]=d['low']; vol[sym]=d['volume']*d['close']
    ff=B+f'{sym}_USDT_USDT-1h-funding_rate.feather'
    if os.path.exists(ff):
        fr=pd.read_feather(ff).set_index('date'); fr.index=pd.to_datetime(fr.index,utc=True)
        fund[sym]=fr['funding_rate']
P={k:pd.DataFrame(v).sort_index() for k,v in dict(close=close,open=opn,high=high,low=low,qvol=vol,funding=fund).items()}
idx=P['close'].index
for k in P: P[k]=P[k].reindex(idx)
P['funding']=P['funding'].fillna(0.0)
os.makedirs('panel',exist_ok=True)
for k,v in P.items(): v.to_parquet(f'panel/{k}_1h.parquet')
print(P['close'].shape, idx[0], idx[-1])
print('funding sample nonzero frac', (P['funding']!=0).mean().mean())
print(P['funding']['BTC'].describe())
start=P['close'].apply(lambda s:s.first_valid_index())
print(start.sort_values().head(5)); print(start.sort_values().tail(5))
print((start<'2021-01-01').sum(),'coins before 2021')
